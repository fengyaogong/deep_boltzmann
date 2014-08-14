This project is essentially abandoned. I wanted to transition this to theano and that required me to abandon einsum, I did this, but, while it worked (give or take) I never found any decent use for it. 

deep_boltzmann
==============
This class intends to implement a deep boltzmann machine as described by [Hinton and Salakhutdinov][5]. There could (might (should)) be a better way to get predictions, but a prediction method using gibbs sampling and masks is implemented.


Planned features include: 


1.  [Bias terms][3] (done)
1.  [Better (Actual) Contrastive Divergence][1] (done)
1.  Persistent Markov upgrade to CD (done)
1.  Greedy layerwise pretraining (done)
2.  [AIS estimation of partition function][2]
3.  Use of DBM to initialize a traditional neural network. (done, naively)
3. [DropOut][6] 
4. [DropConnect][4] (recently removed due to poor performance) 

It also implements a dropout back-propagation for some reasonable definition thereof using stochastic gradient descent.

The whole thing, is, of course, just a prototype, with no guarantees of anything, but it seems to work.


[1]: https://www.cs.toronto.edu/~hinton/absps/efficientDBM.pdf
[2]: http://www.cs.toronto.edu/~rsalakhu/papers/dbn_ais.pdf
[3]: https://www.cs.toronto.edu/~hinton/absps/guideTR.pdf
[4]: http://cs.nyu.edu/~wanli/dropc/dropc.pdf
[5]: https://www.cs.toronto.edu/~hinton/absps/dbm.pdf
[6]: http://arxiv.org/pdf/1207.0580
