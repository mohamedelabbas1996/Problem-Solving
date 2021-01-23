#solution for Xoring Ninja Problem
#https://www.hackerrank.com/challenges/xoring-ninja 
# Enter your code here. Read input from STDIN. Print output to STDOUT
t=int(raw_input())
for _ in xrange(t):
    n=int(raw_input())
    a=map(int,raw_input().split())
    print (reduce(lambda x,y:x | y,a)*2**(n-1))%(7+10**9)