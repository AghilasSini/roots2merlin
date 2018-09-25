
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
import phone_convert 

from shutil import copyfile


# Author : Aghilas SINI
# This code is inspired from TextGrid.py Class Source Code

class Roots2Merlin(object):
    
    file_id_list=[]
    iutt=0 
    def __init__(self,roots_file_name,label_dir_dest,min_utt_dur=1.5,max_utt_dur=5.0,num_utt=60,copy_dest_dir=None,copy=False):
        self.roots_file_name=roots_file_name
        self.label_dir_dest=label_dir_dest
        self.copy=copy
        self.copy_dist_dir=copy_dest_dir
        self.min_utt_dur=min_utt_dur
        self.max_utt_dur=max_utt_dur
        self.num_utt=num_utt

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
                self.file_id_list.append(utt_file_name)
                label_file_name=os.path.join(self.label_dir_dest,utt_file_name+".lab")
                UttByUtt(utt,label_file_name).get_segment_context()
                #for making copy
                if self.copy:
                    label_file_name_copy=os.path.join(self.copy_dest_dir,utt_file_name+".lab")
                    copyfile(label_file_name,label_file_name_copy)
                self.iutt+=1
            utt.destroy()
    
     
    
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

    
            

            
            
            
class UttByUtt(object):
    #varialble
    def __init__(self,utt,label_file_dest,list_sequences_name=None):
        #self.list_sequences_name=list_sequences_name
        self.label_file_dest=label_file_dest
        self.segments=utt.get_sequence('Time Segment JTrans').as_segment_sequence().get_all_items()
        self.syllables=utt.get_sequence('Syllable').as_syllable_sequence().get_all_items()
        
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
        return "{}^{}-{}+{}={}".format(ll_segment_name,l_segment_name,c_segment_name,r_segment_name,rr_segment_name)
    
    
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
                return [isub_item+1,item_length-isub_item]

    #p6-p7
    
    #/A:a1_a2_a3/B:b1-b2-b3
    def get_syllable_structure(self,syllable):
        return len(syllable.get_related_items('Phone JTrans'))
    
    #@b4-b5&b6-b7
    def get_syllable_postion(self,syllable):
        
        
        syl_wrd_fwd,syl_wrd_bwd=self.get_position(syllable.get_related_items('Breath Group')[0],syllable.to_string(),'Syllable')
    
        syl_phrase_fwd,syl_phrase_bwd=self.get_position(syllable.get_related_items('Word JTrans')[0],syllable.to_string(),'Syllable')
        
        
        return "@{}-{}&{}-{}".format(syl_wrd_fwd,syl_wrd_bwd,syl_phrase_fwd,syl_phrase_bwd)
    
    #|b16
    def get_syl_last_phone(self,syllable):
        return "|{}".format(syllable.get_related_items('Phone JTrans')[-1].to_string())
    


   
    def get_segment_context(self):
        phone_label_file=codecs.open(self.label_file_dest,'w','utf-8')
        prev_syl_struct='x'
        for iseg, segment in enumerate(self.segments):
            time_seg=self.get_time_segment(segment)
            c_phone_context=self.get_quinphon(iseg)
            syllables=segment.get_related_items('Syllable')
            if len(syllables)>0:
                icur_syl=syllables[0].get_in_sequence_index()
                cur_syl=self.syllables[icur_syl]
                c_phone_name=self.get_phoneme_name(segment)
                fwd,bwd=self.get_position(cur_syl,c_phone_name,'Phone JTrans')
                seg_syl_pos="{}_{}".format(fwd,bwd)
                if icur_syl>0:
                    prev_syl_struct='{}'.format(self.get_syllable_structure(self.syllables[icur_syl-1]))
                else:
                    prev_syl_struct="x"
                cur_syl_struct="{}".format(self.get_syllable_structure(self.syllables[icur_syl]))
                cur_syl_pos=self.get_syllable_postion(cur_syl)
                cur_last_phone=self.get_syl_last_phone(cur_syl)
                
            else:
                seg_syl_pos="x_x"
                cur_syl_struct='x'
                cur_syl_pos='@x-x&x-x'
                cur_last_phone='|x'
            phone_label_file.write("{} {}@{}/A:{}/B:{}{}{}\n".format(time_seg,c_phone_context,seg_syl_pos,prev_syl_struct,cur_syl_struct,cur_syl_pos,cur_last_phone))
            prev_syl_struct=cur_syl_struct    
        phone_label_file.close()
            
    
    
    def check_out(self):
        return [self.utt.is_valid_sequence(nseq) for nseq in self.list_sequences_name]
    
    


# In[41]:


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



