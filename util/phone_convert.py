import sys
import pandas as pd
import os


def load_map_file(filaname,list_col_name=['timit','sampa']):
	sampa2timit_map=pd.read_csv(filaname,names=list_col_name,sep=',')
	dict_mapping= dict()
	for key,value in zip(sampa2timit_map['sampa'],sampa2timit_map['timit']):
		if not key in dict_mapping.keys():
			dict_mapping[key]=value
	return dict_mapping

def load_default_questions(filename='./util/defaul_questions.csv',list_col_name=["QS","CGS","ALPHA"]):
	default_qs=pd.read_csv(filename,names=list_col_name,sep=';')
	dict_quest=dict()
	for _,key,value in zip(default_qs['QS'],default_qs["CGS"],default_qs["ALPHA"]):
		if not key in dict_quest.keys():
			dict_quest[key]=[ alph for alph in  value.split(',')]
	return dict_quest