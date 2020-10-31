class Node:
    def __init__(self,root,left,right,_min,_max,_value):
        self.range_min = _min
        self.range_max = _max
        self.value = _value
        self.root = root
        self.left = left
        self.right = right
class RangeTree:
    def __init__(self,n):
        self.root = Node(None,None,None,1,n,None)
        self.n = n
        self._build_tree(self.root)
    def traverse(self,root):
        if root == None:
            return
   
       
        self.traverse(root.left)
        #print "left child min {0} max {1}".format(root.range_min , root.range_max)


        print "root min {0} max {1} value {2}".format(root.range_min , root.range_max, root.value)   
        
        self.traverse(root.right)
        #print "right child min {0} max {1}".format(root.range_min , root.range_max) 

            
    
    def _build_tree(self,root):
       # print "build tree min {0} max {1}".format(root.range_min,root.range_max)
           
        if root.range_max == root.range_min:
            return 
        if root.range_max - root.range_min == 1:
            print "build tree min {0} max {1}".format(root.range_min,root.range_max)

            root.right = Node (root,None,None,root.range_max,root.range_max,None)
            root.left = Node (root,None,None,root.range_min,root.range_min,None)
            return
            # self._build_tree(root.right)
            # self._build_tree(root.left)

        if root.range_max < root.range_min:
            root.range_max = root.range_min
            return 


        mid_point = root.range_min + ( root.range_max - root.range_min )/2

        #print root.range_min,mid_point,root.range_max

        root.right = Node (root,None,None,mid_point+1,root.range_max,None)
        root.left = Node (root,None,None,root.range_min,mid_point,None)
        self._build_tree(root.right)
        self._build_tree(root.left)

    
    def change_range_value(self, root,range_min, range_max, value):

        mid_point = root.range_min + (root.range_max - root.range_min)/2
        #assert 1<=range_min<=range_max<=self.n
        if range_min == root.range_min and range_max == root.range_max:
            if root.root != None:
                if root.root.left == root :
                     root.root.right.value = root.root.value
                     root.root.value = None 
                else:
                    root.root.left.value = root.root.value
                    root.root.value = None 


               
              
            if root.value ==None: 
                root.value = value
            else:
                root.value +=value    

            print "value assigned"
            return 

       
        
        # go right
        if range_min>mid_point and range_max <= root.range_max:
            print "Go right"
            print "rootmin {0} rootmax {1} midpoint {2}".format(root.range_min,root.range_max,mid_point)
            print "min {0} max {1}".format(range_min,range_max)

            self.change_range_value(root.right, range_min, range_max,value)
        #go left
        elif range_max<= mid_point and range_min>= root.range_min:
            print "Go left"
            print "rootmin {0} rootmax {1} midpoint {2}".format(root.range_min,root.range_max,mid_point)
            print "min {0} max {1}".format(range_min,range_max)
            self.change_range_value(root.left, range_min, range_max,value)
        #divide
        elif range_min >= root.range_min and range_min <= mid_point and range_max >= mid_point and range_max <= root.range_max:
            print "Go left & right"
            print "left min {0} max {1}  right min {2} max {3}".format(range_min,mid_point,mid_point+1,range_max)
            self.change_range_value(root.left, range_min,mid_point,value)
            self.change_range_value(root.right, mid_point+1,range_max,value)
        else:
            print "else"
            print "min {0} max {1}".format(range_min,range_max)       



def shandom_ruffle_naive(a,b,A):
    a-=1
    b-=1
    bStart = b
    while a<bStart and b<=len(A):
        temp = A[a]
        A[a] = A[b]
        A[b] = temp
        a+=1
        b+=1
    return A

def random_shuffle():
    #handle input
    #n = map(int,raw_input())
    n =4 
    ABs=[(3,1),(1,3),(3,2),(2,3)]


   
    tree = RangeTree(n)
    
    for _ in xrange(n):
        #a,b = map(int,raw_input().split())
        a,b = ABs[_] 
        if (a<b):
            if (b-a< n -b ):    
                tree.change_range_value(tree.root,a,b-1,b-a)
                tree.change_range_value(tree.root,b,2*b-a,a-b)
            else:
                tree.change_range_value(tree.root,a,b,b-a)  
                tree.change_range_value(tree.root,b,n,a-b)  
        else:
            continue
    return tree   

       # ABs.append(map(int,raw_input().split()))
    





def main():
    #print "hello"
    tree =random_shuffle()
    #tree.change_range_value(tree.root,1,3,-1)
    #print 
    #tree.change_range_value(tree.root,2,3,-1)
    tree.traverse(tree.root)
    


if __name__ == "__main__":
    main()    





