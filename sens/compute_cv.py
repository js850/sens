from __future__ import division
import argparse
import numpy as np
import copy
from src.cv_trapezoidal import  compute_cv_c

def compute_Z(energies, T, K, P=1, ndof=0, imp=1, live=False):
    """
    compute the heat capacity and other quantities from nested sampling history
    
    Parameters
    ----------
    energies : list of floats
        list of Emax energy limits
    T : list of floats
        temperatures for which to perform the calculation
    K : int
        number of nested sampling replicas
    P : int
        number of cores used in parallel
    ndof : int
        number of degrees of freedom
        
    Notes
    -----
    from the formula::
    
        alpha = K / (K+1)
        Z = sum_n( (alpha**(n-1) - alpha**(n+1) * np.exp(-beta * energies[n]) )
    
    this can be rewritten::
    
        exp(x) = lim (n->inf) ( (1 + x/n)**n )
        Z = sum_n( (np.exp(-float(n-1) / K) - np.exp(-float(n+1) / K)) * np.exp(-beta * energies[n]) )
    
    or, even better, to try to avoid overflow errors, pull out a factor `np.exp(-float(n-1) / K)`
    
    for parallel, the situation is the same except with a different alpha::
    
        alpha = 1. - float(P) / (K + 1.)

    """
    beta = np.array(1./T)    
    K = float(K)
    E = energies[1:-1]
    n = np.array(xrange(1,len(E)+1), np.float)
    
    # compute the term in the partition function sum for each temperature and each energy
    # lZ[iT, iE] is the contribution to the partition function at temperature 1./beta[iT] from the data at energy E[iE]
    if P == 1:
#        lZ = (-(n[np.newaxis,:]-1.) / K - beta[:,np.newaxis] * E[np.newaxis,:])  + np.log(1. - np.exp(-2. / K))
        lZ = (-(n[np.newaxis,:]) / K - beta[:,np.newaxis] * E[np.newaxis,:])  - np.log(K)
#        lZ = (- beta[:,np.newaxis] * E[np.newaxis,:])  - np.log(K) + n[np.newaxis,:] * np.log(K/(K+1))
#        lZ = (-(n[np.newaxis,:]+1) / K - beta[:,np.newaxis] * E[np.newaxis,:])  - np.log((1.+2*K)/K**2)
#        lZ = (- beta[:,np.newaxis] * E[np.newaxis,:])  - np.log((1.+2*K)/K**2) + (n[np.newaxis,:]+1) * np.log(K/(K+1))
    else:
        if imp is 0:
            a = 1. - float(P) / (K + 1.)
            lZ = n[np.newaxis,:] * np.log(a) + (-beta[:,np.newaxis] * E[np.newaxis,:]) + np.log(1 - a)
        else:
            #this code commented out is wrong but works!!! find out why
            #a = (K-(n[:-K+1]+1)%P)/(K-(n[:-K+1]+1)%P+1)
            #for i in xrange(int(K)-1):
            #    a = np.append(a,(K-i)/(K-i+1))
            #lZ = n[np.newaxis,:] * np.log(a[np.newaxis,:]) + (-beta[:,np.newaxis] * E[np.newaxis,:]) + np.log(1 - a[np.newaxis,:])
            n = np.array(xrange(1,len(E)+1), np.float)
            a = np.floor(n[:]/P) * np.log(1. - float(P) / (K + 1.))
            b = (K - (n[:]%P))/K
            c = (K-(n[:]+2)%P)/(K-(n[:]+2)%P+1)
            #this is what to do if manage to avoid underflow of log(dos) for the live replica energy
            if live is True:
                for i in xrange(int(K)-1):
                    a = np.append( a , np.log(a[-1]*(K-i)/(K-i+1)) )
                    b = np.append(b,1)
                    c = np.append(c, (K-i+1)/(K-i+2))
            lZ =  a[np.newaxis,:] + np.log(b[np.newaxis,:]) + (-beta[:,np.newaxis] * E[np.newaxis,:]) + np.log(1 - c[np.newaxis,:])
            
    # subtract out the smallest value to avoid overflow issues when lZ is exponentiated
    lZmax = np.max(lZ,axis=1) #  maximum lZ for each temperature
    lZ -= lZmax[:,np.newaxis]

    # compute Z, <E> and <E**2> 
    Zpref = np.exp(lZ)
    Z = np.sum(Zpref, axis=1 )
    U = np.sum(Zpref * E[np.newaxis,:], axis=1 )
    U2 = np.sum(Zpref * E[np.newaxis,:]**2, axis=1 )
    
    U /= Z
    U2 /= Z
    # compute Cv from the energy fluctuations
    Cv = (U2 - U**2) * beta**2 + float(ndof)/2 # this is not quite right
    
    lZfinal = np.log(Z) + lZmax
#    Z *= np.exp(lZmax)
        
    return lZfinal, Cv, U, U2


def get_energies(fnames,block=False):
    if len(fnames) == 1:
        return np.genfromtxt(fnames[0])
    if block == False:
        eall = []
        for fname in fnames:
            e = np.genfromtxt(fname)
            eall += e.tolist()
        eall.sort(key=lambda x: -x)
        return np.array(eall).flatten()
    else:
        eall = [[] for i in xrange(len(fnames))]
        for fname,i in zip(fnames,xrange(len(fnames))):
            e = np.genfromtxt(fname)
            eall[i] = copy.deepcopy(e.tolist())
        return np.array(eall)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="load energy intervals and compute cv", 
                                     epilog="if more than one file name is give the energies from all runs will be combined and sorted."
                                     "  the number of replicas will be the sum of the replicas used from all runs (automated!!!)")
#    parser.add_argument("--db", type=str, nargs=1, help="database filename",
#                        default="otp.db")
    parser.add_argument("K", type=int, help="number of replicas")
    parser.add_argument("fname", nargs="+", type=str, help="filenames with energies")
    parser.add_argument("-P", type=int, help="number of cores for parallel run", default=1)
    parser.add_argument("--Tmin", type=float,help="set minimum temperature for Cv evaluation (default=0.01)",default=0.01)
    parser.add_argument("--Tmax", type=float,help="set maximum temperature for Cv evaluation (default=0.5)",default=0.5)
    parser.add_argument("--nT", type=int,help="set number of temperature in the interval Tmin-Tmax at which Cv is evaluated (default=500)",default=500)
    parser.add_argument("--ndof", type=int, help="number of degrees of freedom (default=0)", default=0)
    parser.add_argument("--imp", type=int, help="define whether to use improved Burkoff (use all energies and live replica energies (default=1), otherwise set to 0)", default=1)
    parser.add_argument("--rect", type=int, help="0 for trapezoidal from arithmetic mean (default=0),1 for rectangular from geometric mean (arithmetic if using improved brkf but from python code)", default=0)
    parser.add_argument("--live", action="store_true", help="use live replica energies (default=False), numerically unstable for K>2.5k.",default=False)
    parser.add_argument("--live_not_stored", action="store_true", help="turn this flag on if you're using a set of data that does not contain the live replica.",default=False)
    args = parser.parse_args()
    print args.fname

    energies = get_energies(args.fname,block=False)
    print "energies size", np.size(energies)
#    energies = np.genfromtxt(args.fname)
    
    P = args.P
    print "parallel nprocessors", P
    
    Tmin = args.Tmin
    Tmax = args.Tmax
    nT = args.nT
    dT = (Tmax-Tmin) / nT
    T = np.array([Tmin + dT*i for i in range(nT)])
    
    #in the improved brkf we save the energies of the replicas at the live replica but the ln(dos) underflows for these, hence this:
    if args.live_not_stored == False and args.live is False:
            energies = energies[:-args.K]
    elif args.live_not_stored == True:
        assert args.live == False,"cannot use live replica under any circumstances if they have not been saved" 
    
    #make nd-arrays C contiguous 
    energies = np.array(energies, order='C')
        
    if args.rect is 1:
        print "rectangular"
        lZ, Cv, U, U2 = compute_Z(energies, T, args.K*len(args.fname), P=P, ndof=args.ndof, live=args.live)
    
        with open("cv", "w") as fout:
            fout.write("#T Cv <E> <E**2> logZ\n")
            for vals in zip(T, Cv, U, U2, lZ):
                fout.write("%g %g %g %g %g\n" % vals)
    else:
        print "trapezoidal"
        Cv = compute_cv_c(energies, float(P), float(args.K*len(args.fname)), float(Tmin), float(Tmax), nT, float(args.ndof), args.imp, args.live)
        
        with open("cv", "w") as fout:
            fout.write("#T Cv\n")
            for vals in zip(T, Cv):
                fout.write("%.30f %.30f\n" % vals)
                
    import matplotlib
    matplotlib.use('PDF')
    import pylab as pl
    pl.plot(T, Cv)
    pl.xlabel("T")
    pl.ylabel("Cv")
    pl.savefig("cv.pdf")
        
    
