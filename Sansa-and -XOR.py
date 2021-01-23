#https://www.hackerrank.com/challenges/sansa-and-xor
#solution for Sansa and Xor
t=int(raw_input())
for _ in xrange(t):
    n=int (raw_input())
    a=map(int ,raw_input().split())
    if n%2==0:
        print 0
    else:    
        a=enumerate(a)
        a=filter(lambda x:not x[0]%2,list(a))
        print reduce(lambda x,y:(1,x[1]^y[1]),a)[1]
        