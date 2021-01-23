//Solution for Stones Game Problem
//https://www.hackerrank.com/challenges/stonegame
#include<map>
#include<set>
#include<ctime>
#include<cmath>
#include<queue>
#include<stack>
#include<bitset>
#include<vector>
#include<cstdio>
#include<string>
#include<cassert>
#include<cstring>
#include<numeric>
#include<sstream>
#include<iterator>
#include<iostream>
#include<algorithm>
using namespace std;
typedef long long LL;
#define MM(a,x) memset(a, x, sizeof(a))
#define P(x) cout<<#x<<" = "<<x<<endl;
#define P2(x,y) cout<<#x<<" = "<<x<<", "<<#y<<" = "<<y<<endl;
#define PV(a,n) for(int i=0;i<n;i++) cout<<#a<<"[" << i <<"] = "<<a[i]<<endl;
#define TM(a,b) cout<<#a<<"->"<<#b<<": "<<1.*(b-a)/CLOCKS_PER_SEC<<"s\n";
const int mod = 1000000007;

inline void add(LL &a, LL b) {a = (a + b) % mod;}

LL dp[101][2];

int f(vector<int> p, int N) {
	int n = p.size();
	sort(p.begin(), p.end());
	if(n == 0 || p[n - 1] == 0) return N ? 0 : 1;
	int t = 1;
	for(int i = 0; i < 30; i++) {
		if(p[n - 1] >= (1 << i)) t = 1 << i;
	}
	if(2LL * t <= N) return 0;
	MM(dp, 0);
	dp[0][0] = 1;
	for(int i = 0; i < n - 1; i++) {
		for(int j = 0; j < 2; j++) {
			if(p[i] >= t) {
				add(dp[i + 1][j], dp[i][j] * t);
				add(dp[i + 1][1 - j], dp[i][j] * (p[i] - t + 1));
			} else {
				add(dp[i + 1][j], dp[i][j] * (p[i] + 1));
			}
		}
	}
	LL r = 0;
	if(N < t) {
		r = dp[n - 1][0];
	} else {
		r = dp[n - 1][1];
	}
	vector<int> np = p;
	np[n - 1] -= t;
	r += f(np, N ^ t);
	r %= mod;
	return r;
}

int d[101], n;

int p[101];
LL r;
void brute(int cur, int xr, bool used) {
	if(cur == n) {
		if(xr == 0 && used) {
			r++;		
		}
		return;
	}
	for(int i = 0; i <= d[cur]; i++) {
		p[cur] = i;
		brute(cur + 1, xr ^ i, used | (i == d[cur]));
	}
}

int main() {
		char in[50], out[50];		
		cin >> n;
		for(int i = 0; i < n; i++) cin >> d[i];
		LL ret = 0;
		for(int i = 0; i < n; i++) {
			vector<int> p;
			for(int j = 0; j < n; j++) {
				if(j < i && d[j] > 0) p.push_back(d[j] - 1);
				if(j > i) p.push_back(d[j]);
			}
			add(ret, f(p, d[i]));
		}
		cout << ret << endl;
	return 0;
}