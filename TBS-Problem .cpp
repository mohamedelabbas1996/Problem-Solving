//solution for TBS Problem 
//https://www.hackerrank.com/challenges/tbsp
#include <vector>
#include <algorithm>
#include <cstdio>
#include <cmath>
#include <cstring>

using namespace std;

struct city{
  int x, y;
  double cost;
  double value;
}; 

struct answer{
  vector < int > x, y;
  vector < int > cnt;
  double answer;
};

city a[1 << 17];
int N;
double D;
double C;
answer ret[2];
int idx[2048][2048];
vector < vector < int > > v;
      vector < int > tv;
void scan(){
  scanf ( "%d%lf%lf", &N, &C, &D );
  memset ( idx, -1, sizeof ( idx ) );
  
  for ( int i = 0; i < N; ++i ){
    scanf ( "%d%d%lf", &a[i].x, &a[i].y, &a[i].cost );
    idx[ a[i].x + 1000 ][ a[i].y + 1000 ] = i;
  }
}

bool f ( city t1, city t2 ){
  return t1.value > t2.value;
}

inline double dist ( city t ){
  return sqrt ( (double)t.x * t.x + t.y * t.y );
}

inline double dist ( city t1, city t2 ){
  return sqrt ( (double) ( t1.x - t2.x ) * ( t1.x - t2.x ) + ( t1.y - t2.y ) * ( t1.y - t2.y ) );
}

void go ( int length, int pos ){
  ret[pos].answer = 0;
  ret[pos].x.erase ( ret[pos].x.begin(), ret[pos].x.end() );
  ret[pos].y.erase ( ret[pos].y.begin(), ret[pos].y.end() );
  ret[pos].cnt.erase ( ret[pos].cnt.begin(), ret[pos].cnt.end() );
  v.erase ( v.begin(), v.end() );
  
  for ( int i = 0; i < 2048; i += length )
    for ( int j = 0; j < 2048; j += length ){
      tv.erase ( tv.begin(), tv.end() );
      int ni = min ( i + length, 2048 ), nj = min ( j + length, 2048 );
      for ( int di = i; di < ni; ++di )
	for ( int dj = j; dj < nj; ++dj )
	  if ( idx[di][dj] != -1 )
	    tv.push_back ( idx[di][dj] );
      if ( tv.size() ) v.push_back ( tv );
    }
  
  city last;
  last.x = last.y = 0;
  int brr = 0;
  double penalty = 1.;
  for ( int i = 0; i < (int)v.size(); ++i ){
    double tans = -dist (last);
    vector < int > x, y, cnt;
    city prev;
    prev.x = prev.y = 0;
    double cntt = v[i].size();
    double npenalty = penalty;
    int nbrr = brr;
    if ( brr ){
      x.push_back ( 0 );
      y.push_back ( 0 );
      cnt.push_back ( -1 );
    }
    city nlast = last;
    
    for ( int j = 0; j < (int)v[i].size(); ++j ){
      x.push_back ( a[ v[i][j] ].x );
      y.push_back ( a[ v[i][j] ].y );
      if ( !j )
	cnt.push_back ( v[i].size() );
      else
	cnt.push_back ( -1 );
      tans = tans + ( -dist ( nlast, a[v[i][j]] ) * ( 1 + C * cntt ) ) + a[ v[i][j] ].cost * npenalty;
      nlast = a[v[i][j]];
      --cntt;
      ++nbrr;
      if ( nbrr % ( N / 10 ) == 0 ) npenalty *= D;
    }
    
    if ( tans  < 0 ) continue;
    
    brr = nbrr;
    penalty = npenalty;
    last = nlast;
    for ( int i = 0; i < (int)x.size(); ++i ){
      ret[pos].x.push_back ( x[i] );
      ret[pos].cnt.push_back ( cnt[i] );
      ret[pos].y.push_back ( y[i] );
    }
    ret[pos].answer += tans;
  }
}

void solve(){
  int x = 1;
  go ( x, 0 );
  
  for (; x <= 2000; x *= 2 ){
    go ( x, 1 );
    if ( ret[0].answer < ret[1].answer )
      swap ( ret[0], ret[1] );
  }
  
  for ( int i = 0; i < (int)ret[0].x.size(); ++i ){
    printf ( "%d %d", ret[0].x[i], ret[0].y[i] );
    if ( ret[0].cnt[i] != -1 )
      printf ( " %d", ret[0].cnt[i] );
    printf ( "\n" );
  }
}

int main(){
  scan();
  solve();
}
