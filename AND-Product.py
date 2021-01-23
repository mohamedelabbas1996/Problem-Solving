# Enter your code here. Read input from STDIN. Print output to STDOUT
#solution for AND Product Problem
#https://www.hackerrank.com/challenges/and-product
t=int(raw_input())
for _ in xrange(t):
    a,b=map(int,raw_input().split())
    r=b-a
    (a & b)
    e=""
    for i in xrange(len(bin(b)[2:])):
        if r>=2**i:
            e="0"+e
        else:
            e="1"+e
    print (a&b)&(int(e,2))        
            
        
    
    