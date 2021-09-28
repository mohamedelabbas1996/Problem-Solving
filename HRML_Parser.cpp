#include <cmath>
#include <cstdio>
#include <vector>
#include <map>
#include <iostream>
#include <algorithm>
#include<stack>
using namespace std;

class node {
    public:
    node(string n_name ){
        name = n_name;
        children = new map<string,node>();
        attrs = new map<string,string>();
    }
    string name;
    map<string,string> *attrs ;
    map<string,node>* children;
};

class docTree{
  public :
  docTree(){
      root = new node("root");
  }
  node * root;
  
  
};


class parser{
    public :
    void query(int q){
        
        
        for (int jj=0;jj<q;jj++){
            string node_name ; 
        string attr;
        node * cur = tree->root;
        
            string line = "";
            getline(cin,line);
            
            //cout<<line<<endl;
            bool attr_start = false;
            for (int i =0;i<line.length();i++){
                
                if (line[i]=='.'){
                    //cout<<node_name<<".";
                    cur = &(cur->children->at(node_name));
                    //cout<<"current node name"<<cur->name<<endl;
                    
       
        
                    
                    node_name ="";
                }
                else if (line[i] == '~'){
                    cur = &(cur->children->at(node_name));
                    //cout<<"current node name"<<cur->name<<endl;
                     
        
                    attr_start = true;
                    //cout<<node_name;
                }else{
                    if (attr_start){
                        attr.push_back(line[i]);
                    }else{
                        node_name.push_back(line[i]);
                    }
                }
            } 
          //  cout <<"attr:"<<attr<<endl;
           
            if (cur->attrs->find(attr) != cur->attrs->end()){
                string value = cur->attrs->at(attr);
            cout << value<<endl;
            }else{
                cout << "Not Found!"<<endl;
            }
            
        }
        
    }
    void printTree(){
        auto map = tree->root->children;
        cout<<map->at("tag1").children->at("tag2").attrs->at("name");
        for (std::map<string,node>::iterator it = map->begin();it!=map->end();++it ){
            cout<<it->first;
        }
            //->
    }
    void printFlags(){
        cout<<"after_equal:"<<after_equal<<endl;
        cout<<"attr_start"<<attribute_start<<endl;
        cout<<"value_start"<<value_start<<endl;
        cout<<"tag_name_start"<<tag_name_start<<endl;
    }
    void parse(int n){
        
        node_stack = new stack<node>();
        tree = new docTree();
        current_node = tree->root;
        node_stack->push(*current_node);
        
    map<string , map<string,string>> doc ;
    vector<string> lines ;
   
    
    for (int kk=0;kk<n;kk++){
        
        string line ;
        getline(cin,line);
        //cout<<line<<endl;
        
        for (int i =0;i< line.length();i++){
            
            //cout<<line[i] <<" ";
            //printFlags();
            if (line[i] == '<'){
                tag_name = "";
                tag_name_start = true;
                attribute_start = false;
                value_start = false;
                after_equal = false;
                close_tag = false;
                
            }else if (line[i]=='/'){
                tag_name_start = true;
                close_tag = true;
                
            }
            else if (line[i] == '>'){
               
                
                if (close_tag == false){
                    onTagStartClose(tag_name);
                    
                }else{
                    onTagClose(tag_name);
                }
                
            }
            else if (line[i]=='"'){
                value_start = value_start?false:true;
                
                if (value_start == false){
                    after_equal=false;
                    onValueEnd(tag_name,attribute, value);
                    //cout<<value;
                }else{
                   value = "" ;
                }
            }
            else if (line[i] == '='){
                after_equal = true;
            }
            else if (line[i] == ' '){
                if (tag_name_start){
                    tag_name_start = false;
                    onTagStart(tag_name);
                }
                //cout<<tag_name<<endl<<attribute<<endl<<value;
                if (attribute_start){
                    attribute_start = false;
                    onAttrEnd(tag_name, attribute);
                    //value_start=true;
                }else if (attribute_start==false && after_equal == false){
                    attribute_start = true;
                    attribute = "";
                    
                }
                
            }
            else{
                if (tag_name_start){
                    tag_name.push_back(line[i]);
                }
                if (value_start){
                   
                    value.push_back(line[i]);
                }
                if (attribute_start){
                    attribute.push_back(line[i]);
                }
                
            }
        }
        
        
        
    }
    
    }
    private :
    node * current_node;
    stack<node> * node_stack;
    docTree * tree ;
    bool tag_name_start = false;
        bool tag_name_close = false;
        bool value_start = false;
        bool close_tag = false;
        bool attribute_start = false;
        bool after_equal = false;
        string tag_name;
        string value;
        string attribute;
        
    void onTagStart(string tagName){
        //cout<<"onTagStart"<<endl;
        //cout<<tagName<<endl;
    node * element = new node(tagName);
    current_node = &(node_stack->top());
    current_node->children->insert({tagName,*element}); 
    
        
   node_stack->push(*element);
}

void onTagStartClose(string tagName){
    //cout<<"onTagStartClose"<<endl;
        //cout<<tagName<<endl;
}
void onTagClose(string tagName){
     //cout<<"onTagClose"<<endl;
        //cout<<tagName<<endl;
        node_stack->pop();
}
void onAttrEnd(string tagName,string attr){
     //cout<<"onAttrEnd"<<endl;
        //cout<<tagName<<" "<<attr<<endl;
}
void onValueEnd(string tagName ,string attr,string value){
    
    //cout<<"onValueEnd"<<endl;
        //cout<<tagName<<" "<<attr<<" "<<value<<endl;
       current_node = &(node_stack->top());
        current_node->attrs->insert({attr,value});
        
}
     
};




int main() {
    parser p ;
    int n,q ; 
    cin>>n>>q;
    string emptyline;
    getline(cin,emptyline);
    p.parse(n);
    p.query(q);
    //p.printTree();
    /* Enter your code here. Read input from STDIN. Print output to STDOUT */   
    return 0;
}
 
