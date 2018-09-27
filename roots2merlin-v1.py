
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


# Author : Aghilas SINI
# This code is inspired from TextGrid.py Class Source Code

class Roots2Merlin(object):
    
    file_id_list=[]
    iutt=0 
    dict_questions_corpus={}
    def __init__(self,roots_file_name,label_dir_dest,speaker_name='nadine',min_utt_dur=1.5,max_utt_dur=10.0,num_utt=1160,copy_dest_dir=None,copy=False):
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


    def processing(self,utts):
        print(self.get_roots_file_dirpath())
        for utt in utts:
            sigItem=utt.get_sequence('Signal').get_item(0).as_acoustic_SignalSegment()
            if sigItem.get_segment_duration() > self.min_utt_dur  and sigItem.get_segment_duration() < self.max_utt_dur and self.iutt < self.num_utt:
                utt_file_name,ext=os.path.splitext(sigItem.get_file_name())
                audio_file_orig=os.path.join(self.get_roots_file_dirpath(),sigItem.get_base_dir_name()+"/"+sigItem.get_file_name())
				
                label_id_name=self.speaker_name+'_'+str(self.iutt).zfill(4)
                label_file_name=os.path.join(self.label_dir_dest,label_id_name+".lab")
                audio_file_copy=os.path.join(self.label_dir_dest,label_id_name+".wav")

                self.file_id_list.append(label_id_name)
                utt_prop=UttByUtt(utt,label_file_name,self.dict_questions_corpus)
                utt_prop.get_segment_context()
                self.dict_questions_corpus=utt_prop.get_question_dict()
                copyfile(audio_file_orig,audio_file_copy)	
                #for making copy
                if self.copy:
                    label_file_name_copy=os.path.join(self.copy_dest_dir,utt_file_name+".lab")
                    copyfile(label_file_name,label_file_name_copy)
                self.iutt+=1

            utt.destroy()
        self.print_file_ids('./file_id_list.scp')
        self.print_hed_question_file('./questions-{}.txt'.format(self.speaker_name))
    
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
    def __init__(self,utt,label_file_dest,dict_questions_corpus,list_sequences_name=None):
        #self.list_sequences_name=list_sequences_name
        self.label_file_dest=label_file_dest
        self.dict_questions=dict_questions_corpus
        self.utt=utt
        if self.utt.is_valid_sequence('Time Segment JTrans'):
            self.segments=utt.get_sequence('Time Segment JTrans').as_segment_sequence().get_all_items()
        if self.utt.is_valid_sequence('Syllable'):
            self.syllables=utt.get_sequence('Syllable').as_syllable_sequence().get_all_items()
        if self.utt.is_valid_sequence('Word JTrans'):
            self.words=utt.get_sequence('Word JTrans').as_word_sequence().get_all_items()
        if self.utt.is_valid_sequence('Breath Group'):
            self.phrases=utt.get_sequence('Breath Group').as_symbol_sequence().get_all_items()
            
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
            return "sil"
     
    
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
        for iseg, segment in enumerate(self.segments):
            time_seg=self.get_time_segment(segment)
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
                else:
                    prev_syl_struct="x"
    		#Syllable information ()
                cur_syl_struct="{}".format(self.get_syllable_structure(self.syllables[icur_syl]))
                syl_wrd_fwd,syl_wrd_bwd=self.get_position(cur_syl.get_related_items('Breath Group')[0],cur_syl.to_string(),'Syllable')
                syl_phrase_fwd,syl_phrase_bwd=self.get_position(cur_syl.get_related_items('Word JTrans')[0],cur_syl.to_string(),'Syllable')
                cur_last_phone=self.get_syl_last_phone(cur_syl)
                if icur_syl<len(self.syllables)-1:
                	nex_syl_struct='{}'.format(self.get_syllable_structure(self.syllables[icur_syl+1]))
                else:
                	nex_syl_struct="x"
        		# Word Informations
                cur_word=cur_syl.get_related_items('Word JTrans')[0]
                icur_word=cur_word.get_in_sequence_index()                
                if icur_word>0 and len(self.words[icur_word-1].get_related_items('Pos'))>0:
                	prev_word_nsyl='{}'.format(len(self.words[icur_word-1].get_related_items('Syllable')))
                	prev_word_pos='{}'.format(self.words[icur_word-1].get_related_items('Pos')[0].to_string())
                else:
                	prev_word_nsyl='x'
                	prev_word_pos='x'

                if icur_word<len(self.words) and len(self.words[icur_word+1].get_related_items('Pos'))>0:
                	next_word_nsyl='{}'.format(len(self.words[icur_word+1].get_related_items('Syllable')))
                	next_word_pos='{}'.format(self.words[icur_word+1].get_related_items('Pos')[0].to_string())		
                else:
                	next_word_nsyl='x'
                	next_word_pos='x'

                cur_word_nsyl='{}'.format(len(cur_word.get_related_items('Syllable')))
                if len(cur_word.get_related_items('Pos'))>0:
                	cur_word_pos='{}'.format(cur_word.get_related_items('Pos')[0].to_string())
                else:
                	cur_word_pos='x'
                cur_phrase=cur_word.get_related_items('Breath Group')[0]
                icur_phrase=cur_phrase.get_in_sequence_index()		
                cur_word_in_phrase_fwd,cur_word_in_phrase_bwd=self.get_position(cur_phrase,cur_word.to_string(),'Word JTrans')
        		# Phrase Information		
                if icur_phrase>0:
                	prev_phrase_nwrd='{}'.format(len(self.phrases[icur_phrase-1].get_related_items('Word JTrans')))
                	prev_phrase_nsyl='{}'.format(len(self.phrases[icur_phrase-1].get_related_items('Syllable')))
                else:
                	prev_phrase_nwrd='x'
                	prev_phrase_nsyl='x'
        		
                cur_phrase_nwrd='{}'.format(len(cur_phrase.get_related_items('Word JTrans')))
                cur_phrase_nsyl='{}'.format(len(cur_phrase.get_related_items('Syllable')))
                cur_phrase_in_utt_fwd=icur_phrase+1
                cur_phrase_in_utt_bwd=len(self.phrases)-icur_phrase


                if icur_phrase<len(self.phrases)-1:
                	next_phrase_nwrd='{}'.format(len(self.phrases[icur_phrase+1].get_related_items('Word JTrans')))
                	next_phrase_nsyl='{}'.format(len(self.phrases[icur_phrase+1].get_related_items('Syllable')))
                else:
                	next_phrase_nwrd='x'
                	next_phrase_nsyl='x'
            else:
                seg_in_syl_fwd,seg_in_syl_bwd='x','x'
        		# current syllable properties will all be x
                if icur_syl>0:
                	prev_syl_struct='{}'.format(self.get_syllable_structure(self.syllables[icur_syl-1]))
                else:
                	prev_syl_struct="x"
                if icur_syl<len(self.syllables)-1:
                	nex_syl_struct='{}'.format(self.get_syllable_structure(self.syllables[icur_syl+1]))
                else:
                	nex_syl_struct="x"
                seg_in_syl_fwd,seg_in_syl_bwd='x','x'
                cur_syl_struct='x'
                syl_wrd_fwd,syl_wrd_bwd='x','x'
                syl_phrase_fwd,syl_phrase_bwd='x','x'
                cur_last_phone='x'
        		# current word properties will all be x
                if icur_word>0 and len(self.words[icur_word].get_related_items('Pos'))>0:
                	prev_word_nsyl='{}'.format(len(self.words[icur_word].get_related_items('Syllable')))
                	prev_word_pos='{}'.format(self.words[icur_word].get_related_items('Pos')[0].to_string())
                else:
                	prev_word_nsyl='x'
                	prev_word_pos='x'
        			
                if icur_word<len(self.words) and  len(self.words[icur_word+1].get_related_items('Pos'))>0 and len(self.words[icur_word+1].get_related_items('Syllable'))>0:
                	next_word_nsyl='{}'.format(len(self.words[icur_word+1].get_related_items('Syllable')))
                	next_word_pos='{}'.format(self.words[icur_word+1].get_related_items('Pos')[0].to_string())		
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
                else:
                	prev_phrase_nwrd='x'
                	prev_phrase_nsyl='x'

                if icur_phrase<len(self.phrases)-1:
                	next_phrase_nwrd='{}'.format(len(self.phrases[icur_phrase+1].get_related_items('Word JTrans')))
                	next_phrase_nsyl='{}'.format(len(self.phrases[icur_phrase+1].get_related_items('Syllable')))
                else:
                	next_phrase_nwrd='x'
                	next_phrase_nsyl='x'
                cur_phrase_nwrd='x'
                cur_phrase_nsyl='x'
                cur_phrase_in_utt_fwd='x'
                cur_phrase_in_utt_bwd='x'

            phone_label_file.write('{} '.format(self.get_time_segment(segment)))    
            # segment properties #p1ˆp2-p3+p4=p5@p6_p7
            phone_label_file.write('{}^{}-{}+{}={}@{}_{}'.format(ll_phone,l_phone,c_phone,r_phone,rr_phone,seg_in_syl_fwd,seg_in_syl_bwd))
            # syllables properties #/A:a3/B:b3@b4-b5&b6-b7|b16/C:c3
            phone_label_file.write('/A:{}/B:{}@{}-{}&{}-{}|{}/C:{}'.format(prev_syl_struct,cur_syl_struct,syl_wrd_fwd,syl_wrd_bwd,syl_phrase_fwd,syl_phrase_bwd,cur_last_phone,nex_syl_struct))

            if not cur_last_phone in self.dict_questions.keys():
                self.dict_questions[cur_last_phone]="QS \"C-Syl_{}\" {{|{}/C:}}".format(cur_last_phone,cur_last_phone)
           

            # word properties #/D:d1_d2/E:e1+e2@e3+e4/F:f1_f2
            phone_label_file.write('/D:{}_{}/E:{}+{}s@{}+{}/F:{}_{}'.format(prev_word_pos,prev_word_nsyl,cur_word_pos,cur_word_nsyl,cur_word_in_phrase_fwd,cur_word_in_phrase_bwd,next_word_pos,next_word_nsyl))
            lprev_word_pos='L-Word_GPOS={}'.format(prev_word_pos)
            if not lprev_word_pos in self.dict_questions.keys():
                self.dict_questions[lprev_word_pos]="QS \"{}\" {{/D:{}_}}".format(lprev_word_pos,prev_word_pos)
            ccur_word_pos='C-Word_GPOS={}'.format(cur_word_pos)
            if not ccur_word_pos in self.dict_questions.keys():
                self.dict_questions[ccur_word_pos]="QS \"{}\" {{/E:{}+}}".format(ccur_word_pos,cur_word_pos)
            rnext_word_pos='R-Word_GPOS={}'.format(next_word_pos)
            if not rnext_word_pos in self.dict_questions.keys():
                self.dict_questions[rnext_word_pos]="QS \"{}\" {{/F:{}_}}".format(rnext_word_pos,next_word_pos)
   	
            # phrase properties #/G:g1_g2/H:h1=h2@h3=h4/I:i1_i2
            phone_label_file.write('/G:{}_{}/H:{}={}@{}={}/I:{}_{}'.format(prev_phrase_nsyl,prev_phrase_nwrd,cur_phrase_nsyl,cur_phrase_nwrd,cur_phrase_in_utt_fwd,cur_phrase_in_utt_bwd,next_phrase_nsyl,next_phrase_nwrd))
            # utterance properties # /J:j1+j2-j3 
            phone_label_file.write('/J:{}+{}-{}\n'.format(utt_nbsyllables,utt_nbwords,utt_nphrases))
        phone_label_file.close()
            
    
    

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
    
    


# In[41]


def build_arg_parser():
    parser=argparse.ArgumentParser(description='parse')
    parser.add_argument('in_corpus',type=str,nargs=1,help='roots corpus input file name')
    parser.add_argument('out_phone_label_dir',type=str,nargs=1,help='phone label output file name (merlin)')
    parser.add_argument('copy_dest_dir',type=str,nargs=1,help='phone label output file name (merlin)')
    
    return parser



def main():
    args=build_arg_parser().parse_args()
    roots_file_name=args.in_corpus[0]
    label_dir_dest=args.out_phone_label_dir[0]
    copy_dest_dir=args.copy_dest_dir[0]
    roots2merlin=Roots2Merlin(roots_file_name,label_dir_dest)
    utts=roots2merlin.load_roots_file()
    roots2merlin.processing(utts)

if __name__=='__main__':
    main()



