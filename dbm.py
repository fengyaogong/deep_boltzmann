import numpy
class DBM(object):
    # dataset: a binary valued data matrix
    # labels: the associated outputs for each data row
    # layers: a list containing the size of each hidden layer
    # fantasy_count: The number of markov chains to run in the background
    # learning_rate: starting learning rate. Will be continued harmonically from the starting value.
    def __init__(self,dataset,labels=numpy.array([]),
                batch_size = 500,
                layers=[10,2],
                fantasy_count = 10,
                learning_rate = .0001, ):


        self.dataset = dataset
        self.labels = labels
        self.datapts = dataset.shape[0]
        self.batch_size = batch_size
        self.features = dataset.shape[1]
        self.fantasy_count = fantasy_count
        self.learning_rate = learning_rate
        self.layers = []
        self.layers.append({'layer':'visible',
                            'size':self.features,
                            'fantasy': numpy.random.randint(0,2,(fantasy_count,self.features)).astype(float),
                            'mu':0,
                            'bias': numpy.zeros((1,self.features))})
        for layer in range(len(layers)):
            size = layers[layer]
            hidden = {'layer':'hidden '+str(layer), 'size':size, 'mu':0}
            above = self.layers[-1]['size']
            hidden['W'] = numpy.random.randn(above,size)
            hidden['bias'] = numpy.random.randn(1,size)
            hidden['momentum'] = numpy.zeros((above,size))
            hidden['fantasy'] = numpy.random.randint(0,2,(fantasy_count,size)).astype(float)
            self.layers.append(hidden)
        
    
    #Stochastic annealing scheduler. This one assures that, regardless of
    #  starting value the sequence is in l^2-l^1
    def next_learning_rate(self, rate):
        return 1.0/(1.0/rate+1)
    
    
    def l2_pressure(self,weights):
        norms = numpy.sqrt(numpy.sum(weights*weights, axis=0))
        norms = norms.reshape(norms.shape[0],1)
        norms = norms.T.repeat(weights.shape[0], axis=0)
        return -.01*norms*weights

    #some sigmoid function, this one is fine.
    def sigma(self, x):
        x = numpy.clip(x,-100,100)
        return 1/(1+numpy.exp(-x))

    
    #Quick and dirty bootstrapper to manage samples per epoch
    def data_sample(self, num):
        if self.labels.shape[0] > 0:
            return (self.dataset[numpy.random.randint(0, self.dataset.shape[0], num)],
                self.labels[numpy.random.randint(0, self.labels.shape[0], num)])
        else:
            return (self.dataset[numpy.random.randint(0, self.dataset.shape[0], num)],
                numpy.array([]))


    #Returns activations for probabilities, do not use sigma here, because sampling probs directly.
    def sample(self, fn, args):
        temp = fn(*args)
        temp_cutoff = numpy.random.rand(*temp.shape)
        return (temp >temp_cutoff).astype(float)
    

    #This propagates the test state through the net, 
    #does sigmoid at each layer, and passes that along. 
    # Returns probs at the end, because why not.
    def predict_probs(self, test, prop_uncertainty=False, omit_layers=0): 
        out = test
        for i in range(1,len(self.layers)-omit_layers):
            W=self.layers[i]['W']
            bias = self.layers[i]['bias']
            out = self._predict(W,bias,out)
            if not prop_uncertainty and i< len(self.layers)-1:
                out =numpy.round(out)
        return out
    
    def _predict(self,W,bias,inputs):
        return self.sigma(bias + numpy.dot(inputs,W))


    #The energy of a given layer with a given input and output vector
    def _energy(self,v,W,h,bv,bh):
        return numpy.mean(-numpy.dot(v,bv.T) -numpy.dot(h,bh.T))- numpy.tensordot(numpy.dot(v,W),h, axes=([0,1],[0,1]))

    
    #The energy of the whole DBM with given inputs and hidden activations
    def internal_energy(self, v, hs):
        temp=self._energy(v, self.layers[1]['W'], hs[0],numpy.zeros((1,v.shape[1])),self.layers[1]['bias'])
        for i in range(1, len(self.layers)-1):
            temp += self._energy(hs[i-1], self.layers[i+1]['W'], hs[i], self.layers[i]['bias'], self.layers[i+1]['bias'])
        return temp

    
    #The energy of the network given only the input activiation.
    def energy(self, v):
        hs =  [numpy.round(self.sigma(self.layers[1]['bias']+numpy.dot(v,self.layers[1]['W'])))]
        for i in range(2,len(self.layers)):
            hs.append(numpy.round(self.sigma(self.layers[i]['bias']+numpy.dot(hs[-1], self.layers[i]['W']))))
        return self.internal_energy(v,tuple(hs))
    

    #return the total energy of the stored dataset 
    #and its activation structure given the current model
    def total_energy(self):
        return self.energy(self.dataset)
    

    #return the total entropy of the dataset given the current model.
    def total_entropy(self):
        pred = numpy.clip(self.predict_probs(self.dataset),0.0001,.9999)
        return numpy.sum(self.labels*numpy.log(pred) + (1-self.labels)*numpy.log(1-pred))
    
    
    # prob_given_vis gives a vector of length j with the corresponding probs
    # subset to theappropriate entry to get hj1==1
    def prob_given_vis(self, W, vs,bias):
        return self.sigma(bias + numpy.dot(vs, W))


    #prob_given_out is the same as above, but with the opposite value  and convention.
    def prob_given_out(self, W, hs,bias):
        return self.sigma(bias + numpy.dot( hs, W.T))


    #Tiny gibbs sampler for the fantasy particle updates. The numer of iterations could be controlled, but needn't be
    def gibbs_update(self, gibbs_iterations=100):
        layers = len(self.layers)
        for j in range(gibbs_iterations):
            for i in range(1,layers):
                active = self.layers[i-1]['fantasy']
                bias = self.layers[i]['bias']
                W = self.layers[i]['W']
                self.layers[i]['fantasy'] = self.sample(self.prob_given_vis, (W,active,bias))
            for i in range(layers-1,1,-1):
                active = self.layers[i]['fantasy']
                bias = self.layers[i-1]['bias']
                W = self.layers[i]['W']
                self.layers[i-1]['fantasy'] = self.sample(self.prob_given_out,(W,active,bias))

            


    #This step does the boltzmann part.
    def unsupervised_step(self, data, labels,rate):
        layers=len(self.layers)
        # You could train the last layer too, 
        # but as the last layer communicates the
        # supervised results, this might not help you 
        # so much as just ruin all predictions.
        for i in range(1,layers-1):
            if i==1:
                previous = data
            else:
                previous = self.layers[i-1]['mu']
            bias = self.layers[i]['bias']
            mu = bias+numpy.dot(previous,self.layers[i]['W'])
            #I came up with this bias update scheme. It's not actually
            #in the papers, but it seems reasonable.
            bias_part = mu.mean(axis=0).reshape(*bias.shape)
            self.layers[i]['bias'] = bias + rate*(bias_part-bias)
            mu = self.sigma(mu)
            self.layers[i]['mu'] = mu 
            gradient_part = - 1.0/(self.datapts*self.batch_size) * numpy.dot(previous.T, mu)
            approx_part =- 1.0/self.fantasy_count * numpy.dot(self.layers[i-1]['fantasy'].T,
                                                              self.layers[i]['fantasy'])
            self.layers[i]['W'] =( self.layers[i]['W'] 
                                  + rate *gradient_part 
                                  + rate *approx_part)


    #This is stochastic gradient descent version of a dropout back-propagator.
    def dropout_step(self,data,labels,rate, 
                     dropout_fraction = 0.5, momentum_decay = 0):
        
        layers=len(self.layers)
        for layer in range(layers-1,0,-1):
            W=self.layers[layer]['W']
            dropout = numpy.ones(W.shape)
            while numpy.min(dropout) >=1:
                dropout = (numpy.random.rand(*W.shape)<dropout_fraction).astype(float)
            self.layers[layer]['dropout array']= dropout
            self.layers[layer]['dropped out'] = W*dropout
            W = W-self.layers[layer]['dropped out']
            self.layers[layer]['W']=W
            
        for layer in range(layers-1,0,-1):
            act = self.predict_probs(data)
            prior_act = self.predict_probs(data, omit_layers=layers-layer)
            W = self.layers[layer]['W']
            errors = act - labels
            for iter in range(layers-1, layer,-1):
                source = self.layers[iter]
                errors = source['W'].T*errors

            #output layer
            dropout =  self.layers[layer]['dropout array']

            derivative = act * (1-act) * errors
            errors = act * (1-act)*errors
            gradient = 1.0/self.datapts * numpy.dot(prior_act.T,derivative)
            momentum = momentum_decay*self.layers[layer]['momentum']
            gradient = rate * gradient * (1-dropout)
            W = W - gradient - momentum
            self.layers[layer]['momentum'] = momentum + gradient
            self.layers[layer]['W']=W + self.l2_pressure(W)
            
        for layer in range(layers-1,0,-1):
            W= self.layers[layer]['W']
            W = W+self.layers[layer]['dropped out']  
            self.layers[layer]['W'] = W +0.0001*numpy.random.randn(*W.shape)


    #Train, or continue training the model according to the training schedule for another train_iterations iterations
    def train_unsupervised(self, train_iterations=10000, gibbs_iterations=10):
        for iter in range(train_iterations):
            self.gibbs_update(gibbs_iterations)
            data, labels = self.data_sample(self.batch_size)
            rate = self.learning_rate
            self.unsupervised_step(data,labels,rate)
            self.learning_rate=self.next_learning_rate(self.learning_rate)

    
    #Assuming the data came in with labels, which were disregarded during the unsupervised training.
    def train_dropout(self, train_iterations=10000, weight=1):
        layers=len(self.layers)
        for iter in range(train_iterations):
            rate = self.learning_rate
            rows, labels = self.data_sample(1)
            self.dropout_step(rows, labels, self.learning_rate, rate*weight)               
        self.learning_rate=self.next_learning_rate(self.learning_rate)

    #Okay, so this is an attempt at prediction using a gibbs sampling technique. 
    #The idea is that you feed in an input, but
    #this input is incomplete. You want to make it complete by using 
    #the information in the network, so you update the network, 
    #and sample repeatedly, keeping in mind that the values you want are going 
    #to be set by the mask(==1) and the unknowns will be in flux.
    #the averages of the output values should tell you something.
    #If the mask is none, it will just make up data given your inputs.
    def gibbs_predict(self, input, mask=None,samples = 100,  gibbs_iterations=100):
        input_state = {0:input}
        layers = len(self.layers)
        for i in range(1,layers):
            input_state[i] = numpy.zeros((input.shape[0],self.layers[i]['W'].shape[1]))
        out = []
        for j in range(gibbs_iterations*samples):
            for i in range(1,layers-1):
                active = input_state[i-1]
                bias = self.layers[i]['bias']
                W = self.layers[i]['W']
                input_state[i] = self.sample(self.prob_given_vis, (W,active,bias))
            for i in range(layers-2,0,-1):
                active = input_state[i+1]
                bias = self.layers[i]['bias']
                W = self.layers[i+1]['W']
                input_state[i] = self.sample(self.prob_given_out,(W,active,bias))

            candidate = self.sample(self.prob_given_out, (self.layers[1]['W'], input_state[1],self.layers[0]['bias']))
            if mask is not None:
                input_state[0] = candidate*(1-mask) + input_state[0]*mask 
            else:
                input_state[0]=candidate
            if j%gibbs_iterations == gibbs_iterations-1:
                out.append(input_state[0])
        return out

     
