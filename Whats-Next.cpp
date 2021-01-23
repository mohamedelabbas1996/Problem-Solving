//Solution for What's Next Problem
// https://www.hackerrank.com/challenges/whats-next/

#include <bits/stdc++.h>

#define pb push_back
#define nl puts ("")
#define sp printf ( " " )
#define phl printf ( "hello\n" )
#define ff first
#define ss second
#define POPCOUNT __builtin_popcountll
#define RIGHTMOST __builtin_ctzll
#define LEFTMOST(x) (63-__builtin_clzll((x)))
#define MP make_pair
#define FOR(i,x,y) for(vlong i = (x) ; i <= (y) ; ++i)
#define ROF(i,x,y) for(vlong i = (y) ; i >= (x) ; --i)
#define CLR(x,y) memset(x,y,sizeof(x))
#define UNIQUE(V) (V).erase(unique((V).begin(),(V).end()),(V).end())
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
#define NUMDIGIT(x,y) (((vlong)(log10((x))/log10((y))))+1)
#define SQ(x) ((x)*(x))
#define ABS(x) ((x)<0?-(x):(x))
#define ODD(x) (((x)&1)==0?(0):(1))

using namespace std;

typedef long long vlong;
typedef unsigned long long uvlong;
typedef pair < int, int > pii;
typedef pair < vlong, vlong > pll;
typedef vector<pii> vii;
typedef vector<int> vi;

const vlong inf = 2147383647;
const double pi = 2 * acos ( 0.0 );
const double eps = 1e-9;

vlong arr[1000];
vlong brr[1000];

void solution() {

    int kase;
    scanf ( "%d", &kase );

    while ( kase-- ) {
        int n;
        scanf ( "%d", &n );

        CLR(arr,0);
        CLR(brr,0);

        FOR(i,1,n) {
            scanf ( "%lld", &arr[i] );
        }


        if ( n & 1 ) {
            ///Last is 1

            ///So we update last - 1 position

            vlong temp = arr[n];
            arr[n-1]--;
            if ( arr[n-1] < 0 ) arr[n-1] = 0;
            arr[n] = 1;
            arr[n+1] = 1;
            arr[n+2] = temp - 1;
        }
        else {

            vlong temp = arr[n-1];

            arr[n-2]--;
            if ( arr[n-2] < 0 ) arr[n-2] = 0;
            arr[n-1] = 1;
            arr[n]++;
            arr[n+1] = temp - 1;
        }

        if ( arr[0] ) {
            ROF(i,1,100) {
                arr[i] = arr[i-1];
            }
        }

        ///Now compress the array

        int cur = 1;
        FOR(i,0,n+10) {
            if ( arr[i] == 0 ) {
                continue;
            }

            if ( ODD(cur) && ODD(i) ) {
                brr[cur] = arr[i];
                cur++;
            }
            else if ( !ODD(cur) && !ODD(i) ) {
                brr[cur] = arr[i];
                cur++;
            }
            else {
                ///Add it to previous
                brr[cur-1] += arr[i];
            }
        }

        printf ( "%d\n", cur - 1 );
        FOR(i,1,cur-1) {
            if ( i > 1 ) sp;
            printf ( "%lld", brr[i] );
        }
        nl;
    }
}


int main () {

    solution();

    return 0;
}