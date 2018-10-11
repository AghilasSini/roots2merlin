
# coding: utf-8

# In[40]:


import roots
import sys
import os
import argparse
import glob
import codecs
#inspired from speech features python
import decimal
import math
import numpy
from util.phone_convert import load_default_questions

from shutil import copyfile
import re
from collections import OrderedDict
import subprocess

# multi processing simple and basic
import multiprocessing as mp
import random
import string

from multiprocessing import Manager, Lock


# Author : Aghilas SINI
# This code is inspired from TextGrid.py Class Source Code

class Roots2Merlin(object):
    
    file_id_list=[]
    iutt=0 
    dict_questions_corpus=OrderedDict()
    utts=[]
    def __init__(self,roots_file_name,label_dir_dest,speaker_name='nadine',min_utt_dur=1.5,max_utt_dur=10000,num_utt=4000,copy_dest_dir=None,copy=False):
        self.roots_file_name=roots_file_name
        self.label_dir_dest=label_dir_dest
        self.copy=copy
        self.copy_dist_dir=copy_dest_dir
        self.min_utt_dur=min_utt_dur
        self.max_utt_dur=max_utt_dur
        self.num_utt=num_utt
        self.speaker_name=speaker_name

    def __str__(self):
        return self.roots_file_name

    def __repr__(self):
        return self.roots_file_name
    def get_roots_file_dirpath(self):
        return os.path.dirname(self.roots_file_name)

    def convert_audio_file(self,source_wav_fn,target_wav_fn, target_fs):
        bashCommand = "sox {}  {} rate {}k".format(source_wav_fn,target_wav_fn,target_fs)

        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()

    def solve(self,iutt,utt,sigItem,audio_dir,phone_label_dir,output,lock):
        utt_file_name,ext=os.path.splitext(sigItem.get_file_name())
        audio_file_orig=os.path.join(self.get_roots_file_dirpath(),sigItem.get_base_dir_name()+"/"+sigItem.get_file_name())

        label_id_name=self.speaker_name+'_s'+str(iutt).zfill(4)

        label_file_name=os.path.join(phone_label_dir,label_id_name+".lab")

        audio_file_copy=os.path.join(audio_dir,label_id_name+".wav")

        utt_prop=UttByUtt(utt,label_file_name,self.dict_questions_corpus)
        self.dict_questions_corpus=utt_prop.get_question_dict()
        utt_prop.get_segment_context()
        output.put(label_id_name)
        utt.destroy()
        lock.acquire()
        try:
            self.convert_audio_file(audio_file_orig,audio_file_copy,48)
            utt_prop.pretty_print()
        finally:
            lock.release()






    def processing(self,utts,PROCESSES = 4):
        if not os.path.exists(self.label_dir_dest):
            os.mkdir(self.label_dir_dest)
        print("utt by utt processing start....")
        processes=[]
        output = mp.Queue()
        lock = Lock()
        # issue with this shared variable
        #questions_dict=Manager().dict()
        audio_dir=os.path.join(self.label_dir_dest,'wav')
        if not os.path.exists(audio_dir):
            os.mkdir(audio_dir)
        phone_label_dir=os.path.join(self.label_dir_dest,'label_phone_align')
        if not os.path.exists(phone_label_dir):
            os.mkdir(phone_label_dir)


        for i,utt in enumerate(utts):
            sigItem=utt.get_sequence('Signal').get_item(0).as_acoustic_SignalSegment()
            utt_file_name,ext=os.path.splitext(sigItem.get_file_name())
            if sigItem.get_segment_duration()>self.min_utt_dur and sigItem.get_segment_duration()<self.max_utt_dur and self.iutt<self.num_utt:
                processes.append(mp.Process(target=self.solve,args=(i,utt,sigItem,audio_dir,phone_label_dir,output,lock)))
                self.iutt+=1
            else:
                pass

        for p in processes:
            p.start()
        for p in processes:
            p.join()

        self.file_id_list=[output.get() for p in processes]
        print(self.file_id_list)
        file_id_path=os.path.join(self.label_dir_dest,'file_id_list.scp')
        self.print_file_ids(file_id_path)
        print('questions head file')
        #self.dict_questions_corpus=questions_dict
        question_file_name='questions-{}.txt'.format(self.speaker_name)
        self.print_hed_question_file(os.path.join(self.label_dir_dest,question_file_name))
    
    def load_roots_file(self):
        try:
            corpus=roots.Corpus()
            corpus.load(self.roots_file_name)
            nbutts=corpus.count_utterances()
            return corpus.get_utterances(0,nbutts)
        except FileNotFoundError:
            print("This {} doesn't exits please checkout!".format(self.roots_file_name))
    
    def get_file_id_list(self):
        return self.file_id_list

    def print_file_ids(self,file_list_name):
    	with codecs.open(file_list_name,'w','utf-8') as fn:
	    	for file_name in self.file_id_list:
	    		fn.write(file_name+'\n')
	    	

    def print_hed_question_file(self,questions_file_name):
    	with codecs.open(questions_file_name,'w','utf-8') as fn:
	    	for key,value in zip(self.dict_questions_corpus.keys(),self.dict_questions_corpus.values()):
	    		if isinstance(value,list):
	    			if re.match(r"C-Syl_*",key):
	    				fn.write("QS \"{}\" {{{}}}\n".format(key,",".join(["|"+val+"/C:" for val in set(value) ])))
	    			else:
	    				fn.write("QS \"{}\" {{{}}}\n".format(key, ",".join(["*-"+val+"+*" for val in set(value)])))
	    		else:
	    			fn.write(value+'\n')

            

            
            
            
class UttByUtt(object):
    default_questions_dict=load_default_questions()
    #varialble
    lines=[]
    def __init__(self,utt,label_file_dest,dict_questions_corpus,list_sequences_name=None):
        #self.list_sequences_name=list_sequences_name
        self.label_file_dest=label_file_dest
        self.dict_questions=dict_questions_corpus
        self.utt=utt
        if self.utt.is_valid_sequence('Time Segment JTrans'):
            self.segments=utt.get_sequence('Time Segment JTrans').as_segment_sequence().get_all_items()
        else:
        	sys.exit(-1) 
        if self.utt.is_valid_sequence('Syllable'):
            self.syllables=utt.get_sequence('Syllable').as_syllable_sequence().get_all_items()
        else:
        	sys.exit(-1)
        if self.utt.is_valid_sequence('Word JTrans'):
            self.words=utt.get_sequence('Word JTrans').as_word_sequence().get_all_items()
        else:
        	sys.exit(-1)            
        if self.utt.is_valid_sequence('Breath Group'):
            self.phrases=utt.get_sequence('Breath Group').as_symbol_sequence().get_all_items()
        else:
        	sys.exit(-1)
        # if self.utt.is_valid_sequence('Sentence Bonsai'):
        #     self.sentences=self.utt.get_sequence("Sentence Bonsai").as_symbol_sequence().get_all_items()
        # else:
        #     sys.exit(-1)
        
        if self.utt.is_valid_sequence('POS Stanford'):
        	self.part_of_speech='POS Stanford'
        elif self.utt.is_valid_sequence('Pos'):
        	self.part_of_speech='Pos'
        else:
        	sys.exit(-1)
            
    # beg end
    def get_time_segment(self,segment):
        return "{} {}".format(int(segment.as_acoustic_TimeSegment().get_segment_start()*pow(10,7)),int(segment.as_acoustic_TimeSegment().get_segment_end()*pow(10,7)))
    # p1ˆp 2-p3+p4=p5
    
    def get_quinphon(self, iseg):
        c_segment_name=self.get_phoneme_name(self.segments[iseg])
        if iseg==0:
            ll_segment_name='x'
            l_segment_name='x'
        elif iseg == 1:
            ll_segment_name='x'
            l_segment_name=self.get_phoneme_name(self.segments[iseg-1])
        else:
            ll_segment_name=self.get_phoneme_name(self.segments[iseg-2])
            l_segment_name=self.get_phoneme_name(self.segments[iseg-1])
            
        
        if iseg==len(self.segments)-1:
            r_segment_name='x'
            rr_segment_name='x'
        elif iseg==len(self.segments)-2:
            r_segment_name=self.get_phoneme_name(self.segments[iseg+1])
            rr_segment_name='x'

        else:
            r_segment_name=self.get_phoneme_name(self.segments[iseg+1])
            rr_segment_name=self.get_phoneme_name(self.segments[iseg+2])
        #by default it in sampa (for now)
        # you have to convert this ....  let's try with sampa phoneset then we will see
        return ll_segment_name,l_segment_name,c_segment_name,r_segment_name,rr_segment_name
    
    
    def get_phoneme_name(self,seg):
        phones_segment=seg.get_related_items('Phone JTrans')
        if len(phones_segment)>0:
            return phones_segment[0].to_string()
        else:
            if seg.is_first_in_sequence () or seg.is_last_in_sequence ():
                return "sil"
            else:
                return "pau"
     
    
    def get_position(self,item,sub_item_name,sub_item_seq_name):
        item_subseq=item.get_related_items(sub_item_seq_name)
        item_length=len(item_subseq)
        for isub_item,sub_item in enumerate(item_subseq):
            if sub_item.to_string()==sub_item_name:
                return str(isub_item+1),str(item_length-isub_item)

    #p6-p7

    
    #/A:a1_a2_a3/B:b1-b2-b3
    def get_syllable_structure(self,syllable):
        return len(syllable.get_related_items('Phone JTrans'))
    
  
  
    
    #|b16
    def get_syl_last_phone(self,syllable):
        return "{}".format(syllable.get_related_items('Phone JTrans')[-1].to_string())
    
    
    
    def get_utt_properties(self):
        return  len(self.phrases),len(self.words),len(self.syllables)

    def get_question_dict(self):
    	return self.dict_questions




  #p1ˆp2-p3+p4=p5@p6_p7/A:a3/B:b3@b4-b5&b6-b7|b16/C:c3/D:d1_d2/E:e1+e2@e3+e4/F:f1_f2/G:g1_g2/H:h1=h2@h3=h4/I:i1_i2/J:j1+j2-j3 
    def get_segment_context(self):
        phone_label_file=codecs.open(self.label_file_dest,'w','utf-8')
        utt_nphrases,utt_nbwords,utt_nbsyllables=self.get_utt_properties()
	# initial state of all
        icur_syl=0
        icur_word=0
        icur_phrase=0
        seg_end=0.0
        seg_beg=0.0
        
        for iseg, segment in enumerate(self.segments):
            line=''
	    # p1ˆp2-p3+p4=p5
            ll_phone,l_phone,c_phone,r_phone,rr_phone=self.get_quinphon(iseg)
            cur_syls=segment.get_related_items('Syllable')
            
            qll_phone='LL-{}'.format(ll_phone)

            ql_phone='L-{}'.format(l_phone)

            qc_phone='C-{}'.format(c_phone)

            qr_phone='R-{}'.format(r_phone)

            qrr_phone='RR-{}'.format(rr_phone)

            if not qll_phone in self.dict_questions.keys():
                self.dict_questions[qll_phone]="QS \"LL-{}\" {{*{}^*}}".format(ll_phone,ll_phone)
                
            if not ql_phone in self.dict_questions.keys():
                self.dict_questions[ql_phone]="QS \"L-{}\" {{*^{}-*}}".format(l_phone,l_phone)


            if not qc_phone in self.dict_questions.keys():
                self.dict_questions[qc_phone]="QS \"C-{}\" {{*-{}+*}}".format(c_phone,c_phone)

            if not qr_phone in self.dict_questions.keys():
                self.dict_questions[qr_phone]="QS \"R-{}\" {{*+{}=*}}".format(r_phone,r_phone)
    	    
            if not qrr_phone in self.dict_questions.keys():
                self.dict_questions[qrr_phone]="QS \"RR-{}\" {{*={}@*}}".format(rr_phone,rr_phone)
    	    

    	    # Warning: there is something wrong in this condition
    	    # I think it's okay
            if len(cur_syls)>0:
    		#phones
                icur_syl=cur_syls[0].get_in_sequence_index()
                cur_syl=cur_syls[0]
                c_phone_name=self.get_phoneme_name(segment)
                self.build_up_dict(segment)
    		# p6_p7
                seg_in_syl_fwd,seg_in_syl_bwd=self.get_position(cur_syl,c_phone_name,'Phone JTrans')
    		# a3
                if icur_syl>0:
                    prev_syl_struct='{}'.format(self.get_syllable_structure(self.syllables[icur_syl-1]))
                    prev_syl_style='{}'.format(self.get_syllable_style(self.syllables[icur_syl-1]))
                else:
                    prev_syl_struct="x"
                    prev_syl_style='x'
    		#Syllable information ()
                cur_syl_struct="{}".format(self.get_syllable_structure(self.syllables[icur_syl]))
                cur_syl_style ="{}".format(self.get_syllable_style(self.syllables[icur_syl]))
                syl_wrd_fwd,syl_wrd_bwd=self.get_position(cur_syl.get_related_items('Breath Group')[0],cur_syl.to_string(),'Syllable')
                syl_phrase_fwd,syl_phrase_bwd=self.get_position(cur_syl.get_related_items('Word JTrans')[0],cur_syl.to_string(),'Syllable')
                cur_last_phone=self.get_syl_last_phone(cur_syl)
                if icur_syl<len(self.syllables)-1:
                    nex_syl_struct='{}'.format(self.get_syllable_structure(self.syllables[icur_syl+1]))
                    nex_syl_style='{}'.format(self.get_syllable_style(self.syllables[icur_syl+1]))
                else:
                    nex_syl_struct="x"
                    nex_syl_style="x"
        		# Word Informations
                cur_word=cur_syl.get_related_items('Word JTrans')[0]
                icur_word=cur_word.get_in_sequence_index()                
                if icur_word>0 and len(self.words[icur_word-1].get_related_items(self.part_of_speech))>0:
                	prev_word_nsyl='{}'.format(len(self.words[icur_word-1].get_related_items('Syllable')))
                	prev_word_pos='{}'.format(self.words[icur_word-1].get_related_items(self.part_of_speech)[0].to_string())
                else:
                	prev_word_nsyl='x'
                	prev_word_pos='x'

                if icur_word<len(self.words) and len(self.words[icur_word+1].get_related_items(self.part_of_speech))>0:
                	next_word_nsyl='{}'.format(len(self.words[icur_word+1].get_related_items('Syllable')))
                	next_word_pos='{}'.format(self.words[icur_word+1].get_related_items(self.part_of_speech)[0].to_string())		
                else:
                	next_word_nsyl='x'
                	next_word_pos='x'

                cur_word_nsyl='{}'.format(len(cur_word.get_related_items('Syllable')))
                if len(cur_word.get_related_items(self.part_of_speech))>0:
                	cur_word_pos='{}'.format(cur_word.get_related_items(self.part_of_speech)[0].to_string())
                else:
                	cur_word_pos='x'
                cur_phrase=cur_word.get_related_items('Breath Group')[0]
                icur_phrase=cur_phrase.get_in_sequence_index()		
                cur_word_in_phrase_fwd,cur_word_in_phrase_bwd=self.get_position(cur_phrase,cur_word.to_string(),'Word JTrans')
        		# Phrase Information		
                if icur_phrase>0:
                    prev_phrase_nwrd='{}'.format(len(self.phrases[icur_phrase-1].get_related_items('Word JTrans')))
                    prev_phrase_nsyl='{}'.format(len(self.phrases[icur_phrase-1].get_related_items('Syllable')))
                    prev_phrase_disc=self.add_discours_feat(self.phrases[icur_phrase-1])
                    prev_phrase_emot=self.add_expressivness_feat(self.phrases[icur_phrase-1])
                else:
                    prev_phrase_nwrd='x'
                    prev_phrase_nsyl='x'
                    prev_phrase_disc='x'
                    prev_phrase_emot='x'
        		
                cur_phrase_nwrd='{}'.format(len(cur_phrase.get_related_items('Word JTrans')))
                cur_phrase_nsyl='{}'.format(len(cur_phrase.get_related_items('Syllable')))
                cur_phrase_disc=self.add_discours_feat(cur_phrase)
                cur_phrase_emot=self.add_expressivness_feat(self.phrases[icur_phrase])
                cur_phrase_in_utt_fwd=icur_phrase+1
                cur_phrase_in_utt_bwd=len(self.phrases)-icur_phrase


                if icur_phrase<len(self.phrases)-1:
                    next_phrase_nwrd='{}'.format(len(self.phrases[icur_phrase+1].get_related_items('Word JTrans')))
                    next_phrase_nsyl='{}'.format(len(self.phrases[icur_phrase+1].get_related_items('Syllable')))
                    next_phrase_disc=self.add_discours_feat(self.phrases[icur_phrase+1])
                    next_phrase_emot=self.add_expressivness_feat(self.phrases[icur_phrase+1])
                else:
                    next_phrase_nwrd='x'
                    next_phrase_nsyl='x'
                    next_phrase_disc='x'
                    next_phrase_emot='x'
            else:
                seg_in_syl_fwd,seg_in_syl_bwd='x','x'
        		# current syllable properties will all be x
                if icur_syl>0:
                    prev_syl_struct='{}'.format(self.get_syllable_structure(self.syllables[icur_syl]))
                    prev_syl_style='{}'.format(self.get_syllable_style(self.syllables[icur_syl]))
                else:
                    prev_syl_struct="x"
                    prev_syl_style='x'
                if icur_syl<len(self.syllables)-1:
                    nex_syl_struct='{}'.format(self.get_syllable_structure(self.syllables[icur_syl+1]))
                    nex_syl_style='{}'.format(self.get_syllable_style(self.syllables[icur_syl+1]))
                else:
                    nex_syl_struct="x"
                    nex_syl_style="x"
                seg_in_syl_fwd,seg_in_syl_bwd='x','x'
                cur_syl_struct='x'
                cur_syl_style='x'
                syl_wrd_fwd,syl_wrd_bwd='x','x'
                syl_phrase_fwd,syl_phrase_bwd='x','x'
                cur_last_phone='x'
        		# current word properties will all be x
                if icur_word>0 and len(self.words[icur_word].get_related_items(self.part_of_speech))>0:
                	prev_word_nsyl='{}'.format(len(self.words[icur_word].get_related_items('Syllable')))
                	prev_word_pos='{}'.format(self.words[icur_word].get_related_items(self.part_of_speech)[0].to_string())
                else:
                	prev_word_nsyl='x'
                	prev_word_pos='x'
        			
                if icur_word<len(self.words) and  len(self.words[icur_word+1].get_related_items(self.part_of_speech))>0 and len(self.words[icur_word+1].get_related_items('Syllable'))>0:
                	next_word_nsyl='{}'.format(len(self.words[icur_word+1].get_related_items('Syllable')))
                	next_word_pos='{}'.format(self.words[icur_word+1].get_related_items(self.part_of_speech)[0].to_string())		
                else:
                	next_word_nsyl='x'
                	next_word_pos='x'
                cur_word_nsyl='x'
                cur_word_pos='x'
                cur_phrase='x'
                cur_word_in_phrase_fwd,cur_word_in_phrase_bwd='x','x'
        		# current pĥrase properties will all be x
                if icur_phrase>0:
                    prev_phrase_nwrd='{}'.format(len(self.phrases[icur_phrase].get_related_items('Word JTrans')))
                    prev_phrase_nsyl='{}'.format(len(self.phrases[icur_phrase].get_related_items('Syllable')))
                    prev_phrase_disc=self.add_discours_feat(self.phrases[icur_phrase])
                    prev_phrase_disc=self.add_expressivness_feat(self.phrases[icur_phrase])
                else:
                    prev_phrase_nwrd='x'
                    prev_phrase_nsyl='x'
                    prev_phrase_disc='x'
                    prev_phrase_emot='x'

                if icur_phrase<len(self.phrases)-1:
                    next_phrase_nwrd='{}'.format(len(self.phrases[icur_phrase+1].get_related_items('Word JTrans')))
                    next_phrase_nsyl='{}'.format(len(self.phrases[icur_phrase+1].get_related_items('Syllable')))
                    next_phrase_disc=self.add_discours_feat(self.phrases[icur_phrase+1])
                    next_phrase_emot=self.add_expressivness_feat(self.phrases[icur_phrase+1])
                else:
                    next_phrase_nwrd='x'
                    next_phrase_nsyl='x'
                    next_phrase_disc='x'
                    next_phrase_emot='x'

                cur_phrase_nwrd='x'
                cur_phrase_nsyl='x'
                cur_phrase_disc='x'
                cur_phrase_emot='x'
                cur_phrase_in_utt_fwd='x'
                cur_phrase_in_utt_bwd='x'

            seg_beg=segment.as_acoustic_TimeSegment().get_segment_start()
            if seg_beg==seg_end:
                seg_end= segment.as_acoustic_TimeSegment().get_segment_end()
                line+='{} {} '.format(int(seg_beg*pow(10,7)),int(seg_end*pow(10,7)))
                # segment properties #p1ˆp2-p3+p4=p5@p6_p7
                line+='{}^{}-{}+{}={}@{}_{}'.format(ll_phone,l_phone,c_phone,r_phone,rr_phone,seg_in_syl_fwd,seg_in_syl_bwd)
                # syllables properties #/A:a3-a4/B:b3-b3bis@b4-b5&b6-b7|b16/C:c3_c4
                line+='/A:{}_{}/B:{}-{}@{}-{}&{}-{}|{}/C:{}_{}'.format(prev_syl_struct,prev_syl_style,cur_syl_struct,cur_syl_style,syl_wrd_fwd,syl_wrd_bwd,syl_phrase_fwd,syl_phrase_bwd,cur_last_phone,nex_syl_struct,nex_syl_style)
                lprev_syl_style='L-Syl_Style=={}'.format(prev_syl_style)
                if not lprev_syl_style in self.dict_questions.keys():
                    self.dict_questions[lprev_syl_style]="QS \"{}\" {{_{}/B:}}".format(lprev_syl_style,prev_syl_style)

                ccur_syl_style='C-Syl_Style=={}'.format(cur_syl_style)
                if not ccur_syl_style in self.dict_questions.keys():
                    self.dict_questions[ccur_syl_style]="QS \"{}\" {{-{}@}}".format(ccur_syl_style,cur_syl_style)

                rnext_syl_style='R-Syl_Style=={}'.format(nex_syl_style)    
                if not rnext_syl_style in self.dict_questions.keys():
                    self.dict_questions[rnext_syl_style]="QS \"{}\" {{_{}/C:}}".format(rnext_syl_style,nex_syl_style)


                if not cur_last_phone in self.dict_questions.keys():
                    self.dict_questions[cur_last_phone]="QS \"C-Syl_{}\" {{|{}_}}".format(cur_last_phone,cur_last_phone)
               

                # word properties #/D:d1_d2/E:e1+e2@e3+e4/F:f1_f2
                line+='/D:{}_{}/E:{}+{}@{}+{}/F:{}_{}'.format(prev_word_pos,prev_word_nsyl,cur_word_pos,cur_word_nsyl,cur_word_in_phrase_fwd,cur_word_in_phrase_bwd,next_word_pos,next_word_nsyl)
                lprev_word_pos='L-Word_GPOS=={}'.format(prev_word_pos)
                if not lprev_word_pos in self.dict_questions.keys():
                    self.dict_questions[lprev_word_pos]="QS \"{}\" {{/D:{}_}}".format(lprev_word_pos,prev_word_pos)
                ccur_word_pos='C-Word_GPOS=={}'.format(cur_word_pos)
                if not ccur_word_pos in self.dict_questions.keys():
                    self.dict_questions[ccur_word_pos]="QS \"{}\" {{/E:{}+}}".format(ccur_word_pos,cur_word_pos)
                rnext_word_pos='R-Word_GPOS=={}'.format(next_word_pos)
                if not rnext_word_pos in self.dict_questions.keys():
                    self.dict_questions[rnext_word_pos]="QS \"{}\" {{/F:{}_}}".format(rnext_word_pos,next_word_pos)
       	
                # phrase properties #/G:g1_g2_g2bis_g3/H:h1=h2@h3=h4|h5-h6/I:i1_i2_i2bis_i3
                line+='/G:{}_{}_{}_{}/H:{}={}@{}={}|{}-{}/I:{}_{}_{}_{}'.format(prev_phrase_nsyl,prev_phrase_nwrd,prev_phrase_emot,prev_phrase_disc,cur_phrase_nsyl,cur_phrase_nwrd,cur_phrase_in_utt_fwd,cur_phrase_in_utt_bwd,cur_phrase_disc,cur_phrase_emot,next_phrase_nsyl,next_phrase_nwrd,next_phrase_emot,next_phrase_disc)
                # utterance properties # /J:j1+j2-j3 
                line+='/J:{}+{}-{}\n'.format(utt_nbsyllables,utt_nbwords,utt_nphrases)
            else:
                print("************** Fatal error ***** {} > {} in {}".format(seg_beg,seg_end,self.label_file_dest))
            self.lines.append(line)

    def pretty_print(self):
        with codecs.open(self.label_file_dest,'w','utf-8') as phone_label_file:
            for line in self.lines:
                phone_label_file.write(line)



    def add_expressivness_feat(self, phrase):
        if self.utt.is_valid_sequence('Emotion Label'):
            phrases_emotions=phrase.get_related_items('Emotion Label')
            if len(phrases_emotions):
                emo_label=phrases_emotions[0].to_string(-1)
                if emo_label=='_':
                    return '1'
                else:
                    return '2'
            else:
                return 'x'
        else:
            return numpy.random.choice([2, 1], size=(1,), p=[1./4, 3./4])[0]


    def add_discours_feat(self,phrase):
        if self.utt.is_valid_sequence('Character Label'):
            phrases_discourses=phrase.get_related_items('Character Label')
            if len(phrases_discourses):
                disc_label=phrases_discourses[0].to_string(-1)
                if disc_label=='_':
                    return '1'
                else:
                    return '2'
            else:
                return 'x'
        else:
            return numpy.random.choice([2, 1], size=(1,), p=[1./4, 3./4])[0]

    def get_syllable_style(self,syllable):
        if self.utt.is_valid_sequence('SyllableStyle'):
            syllablestyle=syllable.get_related_items("SyllableStyle")
            if len(syllablestyle):
                sylstyle=syllablestyle[0].to_string(-1)
                if sylstyle=='_':
                    return 'neutral'
                else:
                    return sylstyle
            else:
                return 'x'
        else:
            return 'x'
    def build_up_dict(self,segment):
    	phoneme = segment.get_related_items('Phone JTrans')[0]
    	phoneIpa=phoneme.as_phonology_Phoneme().get_ipa()
    	for key ,values_list in zip(self.default_questions_dict.keys(),self.default_questions_dict.values()):
    		if phoneIpa.to_string() in values_list:
    			if not key in self.dict_questions.keys():
    				self.dict_questions[key]=[phoneme.to_string()]
    			else:
    				self.dict_questions[key].append(phoneme.to_string())
                


    def check_out(self):
        return [self.utt.is_valid_sequence(nseq) for nseq in self.list_sequences_name]
    


# class SentBySent(object):
#     default_questions_dict=load_default_questions()
#     def __init__(self,sentence,utt_file_name,dict_questions_corpus,list_sequences_name=None):
#         self.utt_file_name=utt_file_name
#         self.dict_questions=dict_questions_corpus
#         self.sentence=sentence
#         if self.utt.is_valid_sequence('Time Segment JTrans'):
#             self.segments = [seg.as_acoustic_TimeSegment() for seg in sentence.get_relaled_items('Time Segment JTrans')]
#         else:
#             sys.exit(-1)

#     def sentence_process(self):


# In[41]


def build_arg_parser():
    parser=argparse.ArgumentParser(description='parse')
    parser.add_argument('in_corpus',type=str,nargs=1,help='roots corpus input file name')
    parser.add_argument('out_phone_label_dir',type=str,nargs=1,help='phone label output file name (merlin)')
    parser.add_argument('speaker_name',type=str,nargs=1,help='speaker\'s name')
    parser.add_argument('copy_dest_dir',type=str,nargs=1,help='phone label output file name (merlin)')
    
    return parser



def main():
    args=build_arg_parser().parse_args()
    roots_file_name=args.in_corpus[0]
    label_dir_dest=args.out_phone_label_dir[0]
    speaker_name=args.speaker_name[0]
    copy_dest_dir=args.copy_dest_dir[0]
    roots2merlin=Roots2Merlin(roots_file_name,label_dir_dest,speaker_name=speaker_name)
    utts=roots2merlin.load_roots_file()
    roots2merlin.processing(utts)

if __name__=='__main__':
    main()



