from functools import partial
from pathlib import Path

from data.corpus import Corpus
from data.qe_dataset import QEDataset
from data.fieldsets.fieldset import Fieldset
from data.utils import filter_len, load_vocabularies_to_datasets

def build_vocabulary(fields_vocab_options, *datasets):
    
    def vocab_loaded_if_needed(field):
        return not field.use_vocab or (hasattr(field, 'vocab') and field.vocab)
    
    fields = {}
    for dataset in datasets:
        fields.update(dataset.fields)

    for name, field in fields.items():
        
        if not vocab_loaded_if_needed(field):
            kwargs_vocab = fields_vocab_options[name]
            # delete vectors_fn first
            del kwargs_vocab['vectors_fn']
            
            if 'vectors_fn' in kwargs_vocab:
                vectors_fn = kwargs_vocab['vectors_fn']
                kwargs_vocab['vectors'] = vectors_fn()
                del kwargs_vocab['vectors_fn']
            field.build_vocab(*datasets, **kwargs_vocab)

def build_dataset(fieldset, opt, prefix='', filter_pred=None, **kwargs):
    """
    fields: {'source': data.Field, 'target': data.Field}
    files: {'et': filename, 'ne': filename, 'ro':filename}
    """

    fields, files = fieldset.fields_and_files(prefix, opt, **kwargs)
    corpus = Corpus.from_files(fields=fields, files=files)
    dataset = QEDataset(
        examples=corpus.fields_examples, fields=corpus.dataset_fields, filter_pred=filter_pred
    )
    return dataset

def build_training_datasets(
    fieldset,
    opt,
    split=0.0,
    has_valid=None,
    load_vocab=None
):
    """Build a training and validation QE datasets.
    Required Args:
        fieldset (Fieldset): specific set of fields to be used (depends on
                             the model to be used).
        train_source: Train Source
        train_target: Train Target (MT)
    Optional Args (depends on the model):
        train_target_tags: Train Target Tags
        train_source_tags: Train Source Tags
        train_sentence_scores: Train HTER scores
        valid_source: Valid Source
        valid_target: Valid Target (MT)
        valid_sentence_scores: Valid HTER scores
        split (float): If no validation sets are provided, randomly sample
                       1 - split of training examples as validation set.
        target_vocab_size: Maximum Size of target vocabulary
        source_vocab_size: Maximum Size of source vocabulary
        target_max_length: Maximum length for target field
        target_min_length: Minimum length for target field
        source_max_length: Maximum length for source field
        source_min_length: Minimum length for source field
        target_vocab_min_freq: Minimum word frequency target field
        source_vocab_min_freq: Minimum word frequency source field
        load_vocab: Path to existing vocab file
    Returns:
        A training and a validation Dataset.
    """
    
    filter_pred = partial(
        filter_len,
        source_min_length=opt.lengths.get('source_min_length', 1),
        source_max_length=opt.lengths.get('source_max_length', float('inf')),
        target_min_length=opt.lengths.get('target_min_length', 1),
        target_max_length=opt.lengths.get('target_max_length', float('inf')),
    )
    train_dataset = build_dataset(
            fieldset, 
            opt, 
            prefix=Fieldset.TRAIN, 
            filter_pred=filter_pred
    )
    datasets_for_vocab = [train_dataset]
    if has_valid:
        valid_dataset = build_dataset(
            fieldset,
            opt,
            prefix=Fieldset.VALID,
            filter_pred=filter_pred
        )
        datasets_for_vocab = [train_dataset, valid_dataset]
    elif split:
        if not 0.0 < split < 1.0:
            raise Exception(
                'Invalid data split value: {}; it must be in the '
                '(0, 1) interval.'.format(split)
            )
        train_dataset, valid_dataset = train_dataset.split(split)
    else:
        raise Exception('Validation data not provided.')

    # Handle vocabulary
    if load_vocab:
        vocab_path = Path(load_vocab)
        load_vocabularies_to_datasets(vocab_path, train_dataset, valid_dataset)
    
    fields_vocab_options = fieldset.fields_vocab_options(opt)
    build_vocabulary(fields_vocab_options, *datasets_for_vocab)


    return train_dataset, valid_dataset