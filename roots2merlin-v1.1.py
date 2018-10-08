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
# Author : Aghilas SINI
# This code is inspired from TextGrid.py Class Source Code

class Roots2Merlin(object):
    
    file_id_list=[]
    iutt=0 
    dict_questions_corpus=OrderedDict()
    sentences =[]
    def __init__(self,roots_file_name,label_dir_dest,speaker_name='nadine',num_utt=2000,copy_dest_dir=None,copy=False):
        self.roots_file_name=roots_file_name
        self.label_dir_dest=label_dir_dest
        self.copy=copy
        self.copy_dist_dir=copy_dest_dir
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
   


    def processing(self,utts):
        if not os.path.exists(self.label_dir_dest):
            os.mkdir(self.label_dir_dest)
        print("utt by utt processing start....")
        for utt in utts:
            sigItem=utt.get_sequence('Signal').get_item(0).as_acoustic_SignalSegment()
            utt_file_name,ext=os.path.splitext(sigItem.get_file_name())
            if utt.is_valid_sequence('Sentence Bonsai') and self.iutt<self.num_utt:
                self.sentences=utt.get_sequence('Sentence Bonsai').as_symbol_sequence().get_all_items()
                #
                self.get_sent_full_context(utt_file_name)

            else:
                sys.exit(-1)
            self.iutt+=1

    def get_sent_full_context(self,utt_file_name):
        for isent,sent in enumerate(self.sentences):
            
            sent_file_name=os.path.join(self.label_dir_dest,utt_file_name+"_{}".format(str(isent).zfill(4)))
            SentBySent(sent,sent_file_name,self.dict_questions_corpus).get_full_context()


    def load_roots_file(self):
        try:
            corpus=roots.Corpus()
            corpus.load(self.roots_file_name)
            nbutts=corpus.count_utterances()
            return corpus.get_utterances(0,nbutts)
        except FileNotFoundError:
            print("This {} doesn't exits please checkout!".format(self.roots_file_name))

class SentBySent(object):
    default_questions_dict=load_default_questions()
    def __init__(self,sentence,sent_file_name,dict_questions_corpus,list_sequences_name=None):
        self.sent_file_name=sent_file_name
        self.dict_questions=dict_questions_corpus
        self.sentence=sentence

        # get all segments
        self.segments = [seg.as_acoustic_TimeSegment() for seg in self.sentence.get_related_items('Time Segment JTrans')]
        self.syllables = self.sentence.get_related_items('Syllable')
        self.words =self.sentence.get_related_items('Word Bonsai')
        self.phrases =self.sentence.get_related_items('Breath Group')

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
     


    def get_full_context(self):
        self.get_sent_properties()
        print(self.sent_file_name)
        phone_labe_file= codecs.open(self.sent_file_name,'w','utf-8')
        first_seg_beg=self.segments[0].get_segment_start()
        for iseg,seg in enumerate(self.segments):
            seg_beg=seg.get_segment_start()-first_seg_beg
            seg_end=seg.get_segment_end()-first_seg_beg
            phone_labe_file.write('{} {} '.format(round(seg_beg*pow(10,7)),round(seg_end*pow(10,7))))
            ll_phone,l_phone,c_phone,r_phone,rr_phone=self.get_quinphon(iseg)
            phone_labe_file.write('{}^{}-{}+{}={}\n'.format(ll_phone,l_phone,c_phone,r_phone,rr_phone))
        phone_labe_file.close()

    def get_sent_properties(self):
        print(len(self.phrases),len(self.words),len(self.syllables))

        
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