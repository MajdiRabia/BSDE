import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import leastsq
import pandas as pd
import math
from sklearn.ensemble import RandomForestRegressor


class AmOption(object): 
    
    def __init__(self, S0, K, T, sigma, r, q, oType): 
        self.S0 = S0 
        self.K = K
        self.T = T
        self.sigma = sigma 
        self.r = r
        self.q = q
        self.oType = oType
    
    def generate_paths(self, N, m):
        ''' Function to generate stock paths.

        Parameters
        ==========
        S0    : float
                positive, initial Stock Value
        dt    : float
                time step discretization
        sigma : float 
                volatility 
        r     : float
                bond return 
        N     : int 
                Number of paths generated      
        m     : int 
                number of steps

        Returns
        =======
        S : matrix
            generated paths
        '''
        dt = self.T / m
        S = np.zeros((m + 1, N))
        S[0] = self.S0
        for t in range(1, m + 1):
            rand = np.random.standard_normal(N)
            S[t] = S[t - 1] * np.exp((self.r -self.q- self.sigma ** 2 / 2) * dt + self.sigma * dt ** 0.5 * rand)
        return S
    
    def exercise_matrix(self, S): 
    
        ''' 
        Function to define the ealy exercise matrix.

        Parameters
        ==========
        S     : Matrix
                Stock Values 
        K     : float 
                Strike price

        Returns
        =======
        h : matrix
            early exercise for a call american option
        '''
        if (self.oType == 'call'):
            h = np.maximum(S - self.K, 0)
            return h
        elif (self.oType == 'put'):
            h = np.maximum(self.K - S, 0)
            return h
        else: 
            print ("Enter either a call or put type of option")
        
    
    def pricing_lsm(self, N, m, deg):
  
        dt = self.T / m
        #Discount factor
        df = math.exp(-self.r * dt)
        #Creation of a stock path matrix
        S = self.generate_paths(N, m)
        #Creation of the exercise price matrix
        h = self.exercise_matrix(S)
        #Initialization
        V = h[-1]    

        #Iteration over the paths
        for t in range (m - 2, 0, -1):
            reg = np.polyfit(S[t] ,V ,deg)
            C = np.polyval(reg, S[t])
            V = np.where(h[t] > C, h[t], V * df)

        V_opt= df*np.mean(V)
        return (V_opt)
    
    def pricing_RF(self, N, m, RF_n_estimators,RF_max_leaf_nodes):
        '''
        Function to price the option using Random Forest Regression.

        Parameters
        ========== 
        N               : int 
                          Number of paths generated      
        m               : int 
                          number of steps
        RF_n_estimators : int 
                          Number of trees generated by the Random Forest regression

        RF_max_leaf_    : int 
        nodes             Maximum number of leafs for every branch of the tree generated

        Returns
        =======
        V_opt : float
                Price of the option
        '''  

        #Time-step
        dt = self.T / m
        #Discount factor
        df = math.exp(-self.r*dt)
        #Creation of a stock path matrix
        S = self.generate_paths(N, m)
        #Creation of the exercise price matrix
        h = self.exercise_matrix (S)
        #price of the option at time T = Initialization
        V = h[-1]    

        #Iteration over time
        for t in range (m - 1, 0, -1): 
            X = S[t]
            X = X[:,None]

            #Random Forest algorithm uses the j'th time of the Stock and the (j+1)'th time of Option Price to fit 
            rf = RandomForestRegressor(n_estimators = RF_n_estimators,
                                       max_leaf_nodes=RF_max_leaf_nodes,
                                       oob_score = False, 
                                       n_jobs = -1)
            rf.fit(X, V)
            B = rf.predict(X)
            V = np.where(h[t] > B, h[t], df * V)

        V_opt= df*np.mean(V)
        return (V_opt)

class HDAmOption(object): 
    
    def __init__(self,r, T, K, M, MU, Q, SIGMA, S_init):
        self.T = T
        self.K = K
        self.r = r
        self.M = M 
        self.MU = MU
        self.Q = Q
        self.SIGMA = SIGMA
        self.S_init = S_init
        self.p = len(self.M)
        
    def generate_correlated_paths (self, m):
        dt = self.T / m
        S = np.zeros((m + 1, self.p))
        S[0] = self.S_init
        C = np.linalg.cholesky(self.M)
        for t in range(1, m + 1):
            rand = np.random.standard_normal(self.p)
            rand_int = np.dot(C,rand)
            S[t] = S[t - 1] * np.exp((self.MU - self.Q - self.SIGMA ** 2 / 2) * dt + 
                                     (dt ** 0.5) * self.SIGMA * rand_int)
        return S
       
    def generate_multiple_asset(self, N, m):
        S = []
        #Generate N*p assets
        for __ in range (N):
            S.append(self.generate_correlated_paths(m))
        return (S)    
    
    def exercise_matrix(self, S, N, m, oType, oPayoff): 
        payoff=np.zeros((m + 1, N))
        if (oPayoff == 'geometric'): 
            if (oType == 'call'): 
                for j in range (N): 
                    for i in range (m + 1):
                        pay_int = np.prod( S[j][i,:] ) ** (1 / self.p)
                        pay = max(pay_int - self.K,0)
                        payoff[i,j] = pay
            elif (oType == 'put'): 
                for j in range (N): 
                    for i in range (m + 1):
                        pay_int = np.prod( S[j][i,:] ) ** (1 / self.p)
                        pay = max(self.K - pay_int,0)
                        payoff[i,j] = pay
            else: 
                print ("Enter the type of the option : call or put")
                
        elif (oPayoff == 'arithmetic'):
            if (oType == 'call'): 
                for j in range (N): 
                    for i in range (m + 1):
                        pay_int = np.mean( S[j][i,:] )
                        pay = max(pay_int - self.K,0)
                        payoff[i,j] = pay            
            elif (oType == 'put'): 
                for j in range (N): 
                    for i in range (m + 1):
                        pay_int = np.mean( S[j][i,:] )
                        pay = max(self.K - pay_int,0)
                        payoff[i,j] = pay
                        
        elif (oPayoff == 'max') : 
            if (oType == 'call'): 
                for j in range (N): 
                    for i in range (m + 1):
                        pay_int = np.amax(S[j][i,:])
                        pay = max(pay_int - self.K,0)
                        payoff[i,j] = pay            
            elif (oType == 'put'): 
                for j in range (N): 
                    for i in range (m + 1):
                        pay_int = np.amax(S[j][i,:])
                        pay = max(self.K - pay_int,0)
                        payoff[i,j] = pay
            
        else: 
            print ("You did not enter a possible type of payoff.")
        return (payoff)
    
    def get_price (self, N,m, RF_n_estimators,RF_max_leaf_nodes, 
                   option_type = 'call', option_payoff = 'geometric'):

        #Time-step
        dt = self.T / m
        #Discount factor
        df = np.exp(-self.r * dt)
        #N simulations of p underlying assets
        S = self.generate_multiple_asset(N, m)
        #Matrix of exercise prices
        h = self.exercise_matrix(S, N, m, option_type, option_payoff) 
        #price of the option at time T = Initialization
        V = h [-1]

        #Iteration over the paths"
        for t in range (m - 1, 0, -1): 
            #Creation of the matrix N*p to regress"
            X = np.zeros( [N , self.p] )
            for i in range (N):
                for j in range (self.p): 
                    X[i,j]=S[i][t , j - 1]

            rf=RandomForestRegressor(n_estimators = RF_n_estimators,
                                     max_leaf_nodes = RF_max_leaf_nodes,
                                     oob_score = False, 
                                     n_jobs = -1)
            rf.fit(X, V)
            B = rf.predict(X)
            V = np.where(h[t] > B, h[t], df * V)
            
        V_opt = df * np.mean(V)
        return (V_opt)