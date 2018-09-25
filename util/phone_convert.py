import sys
import pandas as pd
import os


def load_map_file(filaname,list_col_name):
	sampa2timit_map=pd.read_csv(filaname,names=list_col_name,sep=',')
	dict_mapping= dict()
	for key,value in zip(sampa2timit_map['sampa'],sampa2timit_map['timit']):
		if not key in dict_mapping.keys():
			dict_mapping[key]=value
	return dict_mapping

def 



def main():
	load_map_file("./util/sampa2timit.txt",['timit','sampa'])
	

if __name__ == '__main__':
	main()