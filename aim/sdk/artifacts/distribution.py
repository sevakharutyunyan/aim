from abc import ABCMeta, abstractmethod
from typing import Any

from aim.engine.utils import is_pytorch_module, is_tf_module, get_module
from aim.sdk.artifacts.artifact import Artifact
from aim.sdk.artifacts.record import Record, RecordCollection
from aim.sdk.artifacts.utils import get_pt_tensor


class Distribution(Artifact):
    cat = ('distribution',)

    def __init__(self, name: str, dist: Any):
        self.name = name
        self.dist = dist

        super(Distribution, self).__init__(self.cat)

    def __str__(self):
        return '{name}'.format(name=self.name)

    def serialize(self) -> Record:
        return Record(
            name=self.name,
            cat=self.cat,
            content=self.dist,
        )

    def save_blobs(self, name: str, abs_path: str = None):
        pass


class ModelDistribution(Artifact, metaclass=ABCMeta):
    def __init__(self, model: Any):
        self.model = model
        self.hist = self.get_layers(self.model)

        super(ModelDistribution, self).__init__(self.cat)

    def serialize(self) -> RecordCollection:
        records = []
        layers = []

        for name, params in self.hist.items():
            w_dist_name = b_dist_name = ''

            # Serialize layer weights
            if 'weight' in params:
                w_dist_name = '{}__weight'.format(name)
                w_dist = Distribution(w_dist_name, params['weight'])
                records.append(w_dist.serialize())

            # Serialize layer biases
            if 'bias' in params:
                b_dist_name = '{}__bias'.format(name)
                b_dist = Distribution(b_dist_name, params['bias'])
                records.append(b_dist.serialize())

            layers.append({
                'name': name,
                'weight': w_dist_name,
                'bias': b_dist_name,
            })

        return RecordCollection(
            name=self.name,
            cat=self.cat[0],
            records=records,
            data={
                'layers': layers,
            },
        )

    def save_blobs(self, name: str, abs_path: str = None):
        pass

    @staticmethod
    @abstractmethod
    def get_layers(self):
        ...


class WeightsDistribution(ModelDistribution):
    name = 'weights'
    cat = ('weights',)

    @classmethod
    def get_layers(cls, model, parent_name=None):
        np = get_module('numpy')

        layers = {}
        if is_pytorch_module(model):
            for name, m in model.named_children():
                layer_name = '{}__{}'.format(parent_name, name) \
                    if parent_name \
                    else name
                layer_name += '.{}'.format(type(m).__name__)

                if len(list(m.named_children())):
                    layers.update(cls.get_layers(m, layer_name))
                else:
                    layers[layer_name] = {}

                    if hasattr(m, 'weight') \
                            and m.weight is not None \
                            and hasattr(m.weight, 'data'):
                        weight_arr = get_pt_tensor(m.weight.data).numpy()
                        weight_hist = np.histogram(weight_arr, 30)
                        layers[layer_name]['weight'] = [
                            weight_hist[0].tolist(),
                            weight_hist[1].tolist(),
                        ]

                    if hasattr(m, 'bias') \
                            and m.bias is not None \
                            and hasattr(m.bias, 'data'):
                        bias_arr = get_pt_tensor(m.bias.data).numpy()
                        bias_hist = np.histogram(bias_arr, 30)
                        layers[layer_name]['bias'] = [
                            bias_hist[0].tolist(),
                            bias_hist[1].tolist(),
                        ]
        # tf logic goes here
        if is_tf_module(model):
            pass
        return layers


class GradientsDistribution(ModelDistribution):
    name = 'gradients'
    cat = ('gradients',)

    @classmethod
    def get_layers(cls, model, parent_name=None):
        np = get_module('numpy')

        layers = {}
        if is_pytorch_module(model):
            for name, m in model.named_children():
                layer_name = '{}__{}'.format(parent_name, name) \
                    if parent_name \
                    else name
                layer_name += '.{}'.format(type(m).__name__)

                if len(list(m.named_children())):
                    layers.update(cls.get_layers(m, layer_name))
                else:
                    layers[layer_name] = {}

                    if hasattr(m, 'weight') \
                            and m.weight is not None \
                            and hasattr(m.weight, 'grad'):
                        weight_grad_arr = get_pt_tensor(m.weight.grad).numpy()
                        weight_hist = np.histogram(weight_grad_arr, 30)
                        layers[layer_name]['weight'] = [
                            weight_hist[0].tolist(),
                            weight_hist[1].tolist(),
                        ]

                    if hasattr(m, 'bias') \
                            and m.bias is not None \
                            and hasattr(m.bias, 'grad'):
                        bias_grad_arr = get_pt_tensor(m.bias.grad).numpy()
                        bias_hist = np.histogram(bias_grad_arr, 30)
                        layers[layer_name]['bias'] = [
                            bias_hist[0].tolist(),
                            bias_hist[1].tolist(),
                        ]

        return layers
