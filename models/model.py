import torch
import torch.nn as nn
import math

from data.utils import *

class Model(nn.Module):

    subclasses = {}

    def __init__(self, vocabs, opt):

        super(Model, self).__init__()

        self.vocabs = vocabs
        self.opt = opt

    @classmethod
    def register_subclass(cls, subclass):
        cls.subclasses[subclass.__name__] = subclass
        return subclass

    def loss(self, model_out, target):
        pass

    def forward(self, *args, **kwargs):
        pass

    def num_parameters(self):
        return sum(p.numel() for p in self.parameters())
    
    def get_mask(self, batch, output):
        """Compute Mask of Tokens for side.
        Args:
            batch: Namespace of tensors
            side: String identifier.
        """
        side = output

        input_tensor = getattr(batch, side)
        if isinstance(input_tensor, tuple) and len(input_tensor) == 2:
            input_tensor, lengths = input_tensor

        mask = torch.ones_like(input_tensor, dtype=torch.uint8)

        possible_padding = [self.opt.PAD, self.opt.START, self.opt.STOP]
        unk_id = self.vocabs[side].stoi.get(self.opt.UNK)
        for pad in possible_padding:
            pad_id = self.vocabs[side].stoi.get(pad)
            if pad_id is not None and pad_id != unk_id:
                mask &= torch.as_tensor(
                    input_tensor != pad_id,
                    device=mask.device,
                    dtype=torch.uint8,
                )

        return mask
    
    # Load main model path
    @staticmethod
    def create_from_file(path, opt, vocabs=None):

        try:
            model_dict = torch.load(path, map_location=lambda s,l: s)
        except FileNotFoundError:
            # If no model is found
            raise FileNotFoundError(
                'No valid model data found in {}'.format(path)
            )

        for model_name in Model.subclasses:
            if 'Predictor' in model_dict:
                model_dict[model_name] = model_dict['Predictor']
            if model_name in model_dict:
                model = Model.subclasses[model_name].from_dict(model_dict, opt, PreModelClass=opt.pre_model_name, vocabs=vocabs)
                return model
    
    def save(self, path):
        vocabs = serialize_vocabs(self.vocabs)
        model_dict = {
            'vocab': vocabs,
            self.__class__.__name__: {
                'state_dict': self.state_dict(),
            },
        }
        torch.save(model_dict, path)