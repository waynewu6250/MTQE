import logging
from functools import partial

import torch
from torchtext.vocab import Vectors
from torchtext.vocab import GloVe, FastText


logger = logging.getLogger(__name__)


class WordEmbeddings(Vectors):
    def __init__(
        self,
        name,
        emb_format='word2vec',
        binary=True,
        map_fn=lambda x: x,
        **kwargs
    ):
        """
        Arguments:
           emb_format: the saved embedding model format, choices are:
                       polyglot, word2vec, fasttext, glove and text
           binary: only for word2vec, fasttext and text
           map_fn: a function that maps special original tokens
                       to Polyglot tokens (e.g. <eos> to </S>)
           save_vectors: save a vectors cache
        """
        self.binary = binary
        self.emb_format = emb_format

        self.itos = None
        self.stoi = None
        self.dim = None
        self.vectors = None

        self.map_fn = map_fn

        super().__init__(name, **kwargs)

    def __getitem__(self, token):
        if token in self.stoi:
            token = self.map_fn(token)
            return self.vectors[self.stoi[token]]
        else:
            return self.unk_init(torch.Tensor(1, self.dim))

    def cache(self, name, cache, url=None, max_vectors=None):
        if self.emb_format in ['polyglot', 'glove']:
            try:
                from polyglot.mapping import Embedding
            except ImportError:
                logger.error('Please install `polyglot` package first.')
                return None
            if self.emb_format == 'polyglot':
                embeddings = Embedding.load(name)
            else:
                embeddings = Embedding.from_glove(name)
                # embeddings = torchtext.vocab.GloVe(name='840B', dim=300)
            self.itos = embeddings.vocabulary.id_word
            self.stoi = embeddings.vocabulary.word_id
            self.dim = embeddings.shape[1]
            self.vectors = torch.Tensor(embeddings.vectors).view(-1, self.dim)

        elif self.emb_format in ['word2vec', 'fasttext']:
            try:
                from gensim.models import KeyedVectors
            except ImportError:
                logger.error('Please install `gensim` package first.')
                return None
            print("Embedding from wordvec: ", name)
            embeddings = KeyedVectors.load_word2vec_format(
                name, unicode_errors='ignore', binary=self.binary
            )
            self.itos = embeddings.index2word
            self.stoi = dict(zip(self.itos, range(len(self.itos))))
            self.dim = embeddings.vector_size
            self.vectors = torch.Tensor(embeddings.vectors).view(-1, self.dim)


        elif self.emb_format == 'text':
            tokens = []
            vectors = []
            if self.binary:
                import pickle

                # vectors should be a dict mapping str keys to numpy arrays
                with open(name, 'rb') as f:
                    d = pickle.load(f)
                    tokens = list(d.keys())
                    vectors = list(d.values())
            else:
                # each line should contain a token and its following fields
                # <token> <vector_value_1> ... <vector_value_n>
                with open(name, 'r', encoding='utf8') as f:
                    for line in f:
                        if line:  # ignore empty lines
                            fields = line.rstrip().split()
                            tokens.append(fields[0])
                            vectors.append(list(map(float, fields[1:])))
            self.itos = tokens
            self.stoi = dict(zip(self.itos, range(len(self.itos))))
            self.vectors = torch.Tensor(vectors)
            self.dim = self.vectors.shape[1]
        

        # Add bert and XLMR

        # elif self.emb_format == 'bert':  
        elif self.emb_format == 'bert':
            try:
                from transformers import BertTokenizer, BertModel
            except ImportError:
                logger.error('Please install `transformers` package first.')
                return None
            print("Embedding from transformers")
            
            tokenizer = BertTokenizer.from_pretrained('bert-base-multilingual-cased', do_basic_tokenize=True)
            embeddings = BertModel.from_pretrained('bert-base-multilingual-cased').embeddings.word_embeddings.weight
            
            self.itos = tokenizer.ids_to_tokens
            self.stoi = dict(zip(self.itos, range(len(self.itos))))
            self.dim = embeddings.shape[1]
            self.vectors = torch.Tensor(embeddings).view(-1, self.dim)
        
        elif self.emb_format == 'xlmr':
            try:
                from transformers import BertTokenizer, BertModel
            except ImportError:
                logger.error('Please install `transformers` package first.')
                return None
            print("Embedding from transformers")
            
            tokenizer = BertTokenizer.from_pretrained('bert-base-multilingual-cased', do_basic_tokenize=True)
            embeddings = BertModel.from_pretrained('bert-base-multilingual-cased').embeddings.word_embeddings.weight
            
            self.itos = tokenizer.ids_to_tokens
            self.stoi = dict(zip(self.itos, range(len(self.itos))))
            self.dim = embeddings.shape[1]
            self.vectors = torch.Tensor(embeddings).view(-1, self.dim)  


def map_to_polyglot(token):
    mapping = {'<UNK>': '<UNK>', '<PAD>': '<PAD>', '<START>': '<S>', '<EOS>': '</S>'}
    if token in mapping:
        return mapping[token]
    return token


Polyglot = partial(WordEmbeddings, emb_format='polyglot', map_fn=map_to_polyglot)
Word2Vec = partial(WordEmbeddings, emb_format='word2vec')
FastText = partial(WordEmbeddings, emb_format='fasttext')
Glove = partial(WordEmbeddings, emb_format='glove')
TextVectors = partial(WordEmbeddings, emb_format='text')
Bert = partial(WordEmbeddings, emb_format='bert')

AvailableVectors = {
    'polyglot': Polyglot,
    'word2vec': Word2Vec,
    'fasttext': FastText,
    'glove': Glove,
    'text': TextVectors,
    'bert': Bert
}