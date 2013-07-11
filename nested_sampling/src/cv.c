#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <float.h>
double max_array(double* a, int N);
double X_imp(int i, double K, double P);
void compute_dos(double* gl, int N, double P, double K, int live);
void compute_dos_imp(double* gl, int N, double P, double K, int live);
void compute_dos_log(double* gl, int N, double P, double K, int live);
void renorm_energies(double* El, int N, double Emin);
void log_weigths(double* El, double* gl, double* wl, int N, double T, int logscale);
double heat_capacity(double* El, double* gl, int N, double T, double ndof);
void heat_capacity_loop(double* El, double* gl, double* wl, double* Cvl, int N, double Tmin, double Tmax, int nT, double ndof, int logscale);

double max_array(double* a, int N)
{
  int i;
  double max=-DBL_MAX;
  for (i=0; i<N; ++i)
    {
      if (a[i]>max)
	{
	  max=a[i];
	}
    }
  return max;
}

double X_imp(int i, double K, double P)
{
  double X;
  X = (K - (i%(int)P) )/( K - (i%(int)P) + 1);
  return X;
}

void compute_dos(double* gl, int N, double P, double K, int live)
{
  /* gl is an array of 0's of size N, K is the number of replicas */
  int i,j,lim;
  double X = 1 - P/(K+1);
  double Xm = X; //this is X1
  double Xf, Xb;
  Xb = 2-X; /* reflecting boundary condition, this is X0 */
  Xf = Xm * X; 
  gl[0] = 0.5 * (Xb - Xf);
  if (live == 1)
    {
      lim = (N-K-1);
    }
  else
    {
      lim = (N-1);
    }
  for(i=1;i<lim;++i)
    {
      Xb = Xm;
      Xm = Xf;
      Xf = Xm * X;
      gl[i] = 0.5 * (Xb - Xf);
    }
  /*calculate density of states for live replica energies (if flag is on) */
  if (live == 1)
    {
      j=0;
      for(i=lim;i<(N-1);++i)
	{
	  Xb = Xm;
	  Xm = Xf;
	  Xf = Xm * (K-j)/(K-j+1);
	  gl[i] = 0.5 * (Xb - Xf);
	  ++j;
	}
    }
  Xb = Xm;
  Xm = Xf;
  Xf = -Xm;
  gl[N-1] =  0.5 * (Xb - Xf);  
}

void compute_dos_imp(double* gl, int N, double P, double K, int live)
{
  // gl is an array of 0's of size N, K is the number of replicas
  int i,j,lim;
  double Xm = X_imp(0,K,P); //this is X1
  double Xf, Xb;
  Xb = 2-Xm; // reflecting boundary condition, this is X0
  Xf = Xm * X_imp(1,K,P); 
  gl[0] = 0.5 * (Xb - Xf);
  //calculate density of states for stored energies, don't do it because of numerical instability
  //for(i=1;i<(N-K-1);++i) when using live replica
  if (live == 1)
    {
      lim = (N-K-1);
    }
  else
    {
      lim = (N-1);
    }
  for(i=1;i<lim;++i)
    {
      //printf("Xm %E \n",Xm);
      Xb = Xm;
      Xm = Xf;
      Xf = Xm * X_imp(i+1,K,P);
      gl[i] = 0.5 * (Xb - Xf);
    }
  //calculate density of states for live replica energies (if flag is on)
  if (live == 1)
    {
      j = 0;
      for(i=lim;i<(N-1);++i)
	{
	  Xb = Xm;
	  Xm = Xf;
	  Xf = Xm * (K-j)/(K-j+1);
	  gl[i] = 0.5 * (Xb - Xf);
	  ++j;
	}
    }
  Xb = Xm;
  Xm = Xf;
  Xf = -Xm;
  gl[N-1] =  0.5 * (Xb - Xf);  
}

void compute_dos_log(double* gl, int N, double P, double K, int live)
{
  // gl is an array of 0's of size N, K is the number of replicas
  int i,j,lim;
  double Xf;
  double G;
  double alpha = 1 - P/(K+1);
  double m, s;
  //step i =0, m here is Xb
  m = log(2. - X_imp(0,K,P)); // reflecting boundary condition, this is X0 
  gl[0] = log(0.5) + m + log(1-X_imp(0,K,P)*X_imp(1,K,P));
  //calculate density of states for stored energies, don't do it because of numerical instability
  //for(i=1;i<(N-K-1);++i) when using live replica
  
  if (live == 1)
    {
      lim = (N-K-1);
    }
  else
    {
      lim = (N-1);
    }
  for(i=1;i<lim;++i)
    {
      s = floor(i/P);
      G = i - s*P;
      m += log(X_imp(i-1,K,P));
      gl[i] = log(0.5) + m + log(1 - (( K - ((int)G%(int)P)) / (K+1-((int)G%(int)P))) * ((K-((int)(G+1)%(int)P)) / (K+1-((int)(G+1)%(int)P)) ) );
      //printf("gl[%d] is %E \n",i, gl[i]);
    }
  //calculate density of states for live replica energies (if flag is on)
  if (live == 1)
    {
      m += log(X_imp(i,K,P));
      j = 0;
      for(i=lim;i<(N-1);++i)
	{
	  s = floor(i/P);
	  gl[i] = log(0.5) + m + log(1 - (K-j)/(K-j+1) * (K-(j+1))/(K-(j+1)+1));
	  m += log((K-j)/(K-j+1));
	  ++j;
	}
      ++i;
      s = floor(i/P);
      m -= log((K-(j-1))/(K-(j-1)+1));
      Xf = -(K-j)/(K-j+1);
      gl[N-1] = log(0.5) + m + log(1 - (K-j)/(K-j+1) * Xf);
    }
  else
    {
      ++i;
      s = floor(i/P);
      m += log(X_imp(i-1,K,P));
      G = i - s*P;
      Xf = - (K-((int)G%(int)P)) / ( K + 1 - ((int)G%(int)P) );
      gl[N-1] = log(0.5) + m + log(1 - (K-(((int)G%(int)P))/(K+1-((int)G%(int)P))) * Xf);
    }
}

void log_weigths(double* El, double* gl, double* wl, int N, double T, int logscale)
{
  int i;
  double beta = 1/T;
  if (logscale == 1)
    {
      for(i=0;i<N;++i)
	{
	  wl[i] = gl[i] - beta * El[i];
	}
    }
  else
    {
      for(i=0;i<N;++i)
	{
	  if(gl[i]<0)
	    {
	      printf("gl[%d] is %E \n",i, gl[i]);
	      abort();
	    }
	  wl[i] = log(gl[i]) - beta * El[i];
	}
    }
}

////////////renormalise energies wrt ground state/////////////////
void renorm_energies(double* El, int N, double Emin)
{
  int i;
  for(i=0;i<N;++i)
  {
    El[i] -= Emin;
  }
}

////////////////////////////caclulate heat capacity for a single T////////////////////////
double heat_capacity(double* El, double* wl, int N, double T, double ndof)
{
  //K is the number of replicas, beta the reduced temperature and E is the array of energies 
  int i;
  double Cv;
  double Z = 0;
  double U = 0;
  double U2 = 0;
  double beta = 1/T;
  double bolz = 0.;
  
  for(i=0;i<N;++i)
  {
    bolz = exp(wl[i]);
    Z += bolz;
    //printf("Z %E \n",Z);
    U += El[i] * bolz;
    U2 += El[i] * El[i] * bolz;
  }

  U /= Z;
  U2 /= Z;
  Cv =  (U2 - U*U)*beta*beta + ndof/2;
  //printf("Z U U2 Cv %E %E %E %E \n",Z,U,U2,Cv);
  return Cv;
}

//////////////////////////////calculate heat capacity over a set of Ts/////////////////////
void heat_capacity_loop(double* El, double* gl, double* wl, double* Cvl, int N, double Tmin, double Tmax, int nT, double ndof, int logscale)
{
  //Cvl is a 0's array of size N (same size as El)
  int i,j;
  double dT = (Tmax - Tmin) / nT;
  double T = Tmin;
  double wl_max;
  
  for(i=0;i<nT;++i)
  {
    log_weigths(El, gl, wl, N, T, logscale);
    wl_max = max_array(wl,N);
    
    //printf("wl_max %d \n",wl_max);
    
    for(j=0;j<N;++j)
      {
	wl[j] -= wl_max;
      }
    
    Cvl[i] = heat_capacity(El, wl, N, T, ndof);
    T += dT;
  }
}
