import torch
import numpy as np
import glob

from data.fieldsets.build_fieldsets import build_fieldset
from data.builders import build_training_datasets, build_test_dataset
from data.iterators import build_bucket_iterator
from data.utils import *
from data.corpus import Corpus
from trainers.utils import retrieve_trainer
from config import opt
from models import Model, BilstmPredictor, Estimator, TransformerPredictor

from predictors.utils import setup_output_directory, configure_seed
from predictors.predictors import Predicter
from metrics.functions import *

def predict():
    
    # Setup
    output_dir = setup_output_directory(opt.pred_path, create=True)
    configure_seed(opt.seed)
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    
    # Model
    ModelClass = eval(opt.model_name)
    model = ModelClass.create_from_file(opt.model_path, opt)
    model = model.to(device)
    predicter = Predicter(model, opt)

    # Data
    fieldset = build_fieldset(opt)
    test_dataset = build_test_dataset(fieldset, opt, load_vocab=opt.model_path) # build vocabs from model?
    #test_dataset = build_test_dataset(fieldset, opt)
    #vocabs = fields_to_vocabs(test_dataset.fields)  # build vocab from test dataset?
    print('Source vocabulary size: ', len(test_dataset.fields['source'].vocab.stoi))
    print('Target vocabulary size: ', len(test_dataset.fields['target'].vocab.stoi))

    test_iter = build_bucket_iterator(
        test_dataset,
        batch_size=opt.test_batch_size,
        is_train=False,
        device=device
    )
    for i, batch in enumerate(test_iter):
        #print(batch.target[0])
        s = ""
        for j in batch.target[0]:
            s += " " + test_dataset.fields['target'].vocab.itos[j.item()]
        print(i)
        print(s)
        

    predictions = predicter.run(test_iter, batch_size=opt.test_batch_size)
    save_predicted_probabilities(opt.pred_path, predictions)

def evaluate():
    ## Ground-truth (z_mean)
    file_path = opt.paths['test']
    gt = []
    for filename in glob.glob(file_path + '*/*.tsv'):
        pdata = Corpus.read_tabular_file(filename)
        #print(len(pdata['z_mean']))
        gt.extend(pdata['z_mean'])
    gt = np.array(gt).astype(float)

    ## Predictions
    pred_file = opt.pred_path + 'scores'
    preds = np.array([line.strip() for line in open(pred_file)], dtype="float")

    ## Evaluate
    scores, ranks = eval_sentence_level(gt, preds)
    print_sentences_scoring_table(scores)
    print_sentences_ranking_table(ranks)

def train():

    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

    # Data
    fieldset = build_fieldset(opt)
    
    if opt.model_name == 'Estimator':
        train_dataset, valid_dataset = build_training_datasets(fieldset, opt, split = 0.8, has_valid=False, load_vocab=opt.load_pred_source)
    else:
        train_dataset, valid_dataset = build_training_datasets(fieldset, opt, split = 0.8, has_valid=False)

    vocabs = fields_to_vocabs(train_dataset.fields)

    # Call vocabulary
    print('Source vocabulary size: ', len(fieldset.fields['source'].vocab.itos))
    print('Target vocabulary size: ', len(fieldset.fields['target'].vocab.itos))
    print()
    
    # Trainer
    ModelClass = eval(opt.model_name)
    trainer = retrieve_trainer(ModelClass, opt, vocabs, device)

    # Dataset iterators
    train_iter = build_bucket_iterator(
        train_dataset,
        batch_size=opt.train_batch_size,
        is_train=False,
        device=device
    )
    valid_iter = build_bucket_iterator(
        valid_dataset,
        batch_size=opt.valid_batch_size,
        is_train=False,
        device=device
    )

    # Run training
    trainer.run(train_iter, valid_iter, opt)
    

    # for batch in valid_iter:
    #     s_train = ""
    #     for j in batch.source[0]:
    #         s_train += " " + train_dataset.fields['source'].vocab.itos[j.item()]
    #     st_train = ""
    #     for j in batch.target[0]:
    #         st_train += " " + train_dataset.fields['target'].vocab.itos[j.item()]
    #     s = ""
    #     for j in batch.source[0]:
    #         s += " " + valid_dataset.fields['source'].vocab.itos[j.item()]
    #     st = ""
    #     for j in batch.target[0]:
    #         st += " " + valid_dataset.fields['target'].vocab.itos[j.item()]
        
    #     print(batch.source[0])
    #     print(batch.target[0])
    #     print(s_train)
    #     print(st_train)
    #     print(s)
    #     print(st)
    #     break

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Put arguments for train, predict, or evaluate')
    parser.add_argument('-m', '--mode', dest='mode', default='train', help='Input the mode: train, predict or evaluate')
    args = parser.parse_args()
    if args.mode == 'train':
        train()
    elif args.mode == 'predict':
        predict()
    elif args.mode == 'evaluate':
        evaluate()
    else:
        pass