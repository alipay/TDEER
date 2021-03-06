# -*- coding: utf-8 -*-

""" Yet another transformer implementation.
"""

# TODO: Transformer Decoder

import math
from typing import Optional, List, Union, Any

from langml import TF_KERAS
if TF_KERAS:
    import tensorflow.keras as keras
    import tensorflow.keras.backend as K
    import tensorflow.keras.layers as L
else:
    import keras
    import keras.backend as K
    import keras.layers as L

from langml.tensor_typing import Number, Tensors, Activation, Initializer, Constraint, Regularizer


def gelu(x: Number) -> Number:
    r""" Gaussian Error Linear Units (GELUs)
    https://arxiv.org/abs/1606.08415

    $GELU(x) = 0.5x(1 + tanh[\sqrt(2 / \Pi) (x + 0.044715x^3)])$
    """

    return 0.5 * x * (1.0 + K.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x**3)))


class FeedForward(L.Layer):
    """ Feed Forward Layer
    https://arxiv.org/pdf/1706.03762.pdf
    """
    def __init__(self,
                 units,
                 activation: Optional[Activation] = 'relu',
                 kernel_initializer: Optional[Initializer] = 'glorot_normal',
                 kernel_regularizer: Optional[Regularizer] = None,
                 kernel_constraint: Optional[Constraint] = None,
                 bias_initializer: Optional[Initializer] = 'zeros',
                 bias_regularizer: Optional[Regularizer] = None,
                 bias_constraint: Optional[Constraint] = None,
                 use_bias: Optional[bool] = True,
                 dropout_rate: float = 0.0,
                 **kwargs):
        super(FeedForward, self).__init__(**kwargs)
        self.supports_masking = True
        self.units = units
        self.activation = keras.activations.get(activation)
        self.kernel_initializer = keras.initializers.get(kernel_initializer)
        self.kernel_regularizer = keras.regularizers.get(kernel_regularizer)
        self.kernel_constraint = keras.constraints.get(kernel_constraint)
        self.bias_initializer = keras.initializers.get(bias_initializer)
        self.bias_regularizer = keras.regularizers.get(bias_regularizer)
        self.bias_constraint = keras.constraints.get(bias_constraint)
        self.use_bias = use_bias
        self.dropout_rate = dropout_rate

    def get_config(self) -> dict:
        config = {
            "units": self.units,
            "activation": keras.activations.serialize(self.activation),
            "kernel_initializer": keras.initializers.serialize(self.kernel_initializer),
            "kernel_regularizer": keras.regularizers.serialize(self.kernel_regularizer),
            "kernel_constraint": keras.constraints.serialize(self.kernel_constraint),
            "bias_initializer": keras.initializers.serialize(self.bias_initializer),
            "bias_regularizer": keras.regularizers.serialize(self.bias_regularizer),
            "bias_constraint": keras.constraints.serialize(self.bias_constraint),
            "use_bias": self.use_bias,
            "dropout_rate": self.dropout_rate
        }
        base_config = super(FeedForward, self).get_config()

        return dict(base_config, **config)

    def build(self, input_shape: Tensors):
        feature_dim = int(input_shape[-1])
        self.W1 = self.add_weight(
            shape=(feature_dim, self.units),
            initializer=self.kernel_initializer,
            regularizer=self.kernel_regularizer,
            constraint=self.kernel_constraint,
            name=f'{self.name}_W1',
        )
        self.W2 = self.add_weight(
            shape=(self.units, feature_dim),
            initializer=self.kernel_initializer,
            regularizer=self.kernel_regularizer,
            constraint=self.kernel_constraint,
            name='{}_W2'.format(self.name),
        )
        if self.use_bias:
            self.b1 = self.add_weight(
                shape=(self.units,),
                initializer=self.bias_initializer,
                regularizer=self.bias_regularizer,
                constraint=self.bias_constraint,
                name='{}_b1'.format(self.name),
            )
            self.b2 = self.add_weight(
                shape=(feature_dim,),
                initializer=self.bias_initializer,
                regularizer=self.bias_regularizer,
                constraint=self.bias_constraint,
                name='{}_b2'.format(self.name),
            )
        if self.dropout_rate > 0.0:
            self.dropout_layer = L.Dropout(self.dropout_rate)
        super(FeedForward, self).build(input_shape)

    def call(self,
             inputs: Tensors,
             mask: Optional[Tensors] = None,
             training: Optional[Any] = None,
             **kwargs) -> Union[List[Tensors], Tensors]:
        hidden = K.dot(inputs, self.W1)
        if self.use_bias:
            hidden = K.bias_add(hidden, self.b1)
        if self.activation is not None:
            hidden = self.activation(hidden)
        if self.dropout_rate > 0.0:
            hidden = self.dropout_layer(hidden)
        output = K.dot(hidden, self.W2)
        if self.use_bias:
            output = K.bias_add(output, self.b2)
        return output

    def compute_mask(self,
                     inputs: Tensors,
                     mask: Optional[Union[Tensors, List[Tensors]]] = None) -> Union[
                         List[Union[Tensors, None]], Tensors]:
        return mask

    @staticmethod
    def get_custom_objects() -> dict:
        return {'FeedForward': FeedForward}

    def compute_output_shape(self, input_shape: Tensors) -> Tensors:
        return input_shape


class SineCosinePositionEmbedding(L.Layer):
    """Sine Cosine Position Embedding.
    https://arxiv.org/pdf/1706.03762
    """

    def __init__(self,
                 mode: Optional[str] = 'add',
                 output_dim: Optional[int] = None,
                 **kwargs):
        """
        # mode:
          expand
            # Input shape
                2D tensor with shape: `(batch_size, sequence_length)`.
            # Output shape
                3D tensor with shape: `(batch_size, sequence_length, output_dim)`.
          add
            # Input shape
                3D tensor with shape: `(batch_size, sequence_length, feature_dim)`.
            # Output shape
                3D tensor with shape: `(batch_size, sequence_length, feature_dim)`.
          concat
            # Input shape
                3D tensor with shape: `(batch_size, sequence_length, feature_dim)`.
            # Output shape
                3D tensor with shape: `(batch_size, sequence_length, feature_dim + output_dim)`.
        """
        self.supports_masking = True
        assert mode in ['expand', 'add', 'concat'], f'not support mode `{mode}`, options: expand | add | concat'
        if mode in ['expand', 'concat']:
            if output_dim is None:
                raise NotImplementedError(f'`output_dim` is required in `{mode}` mode')
            if output_dim % 2 != 0:
                raise NotImplementedError(f'Not support an odd output dimension: {output_dim}')
        self.mode = mode
        self.output_dim = output_dim
        super(SineCosinePositionEmbedding, self).__init__(**kwargs)

    def get_config(self):
        config = {
            'mode': self.mode,
            'output_dim': self.output_dim,
        }
        base_config = super(SineCosinePositionEmbedding, self).get_config()

        return dict(base_config, **config)

    @staticmethod
    def get_custom_objects() -> dict:
        return {'SineCosinePositionEmbedding': SineCosinePositionEmbedding}

    def compute_mask(self, inputs: Tensors, mask: Optional[Tensors] = None) -> Union[Tensors, None]:
        return mask

    def compute_output_shape(self, input_shape: Tensors) -> Tensors:
        if self.mode == 'expand':
            return input_shape + (self.output_dim,)
        if self.mode == 'concat':
            return input_shape[:-1] + (input_shape[-1] + self.output_dim,)
        return input_shape

    def call(self, inputs: Tensors, mask: Optional[Tensors] = None, **kwargs) -> Tensors:
        input_shape = K.shape(inputs)
        batch_size, seq_len = input_shape[0], input_shape[1]
        output_dim = input_shape[2] if self.mode == 'add' else self.output_dim
        if self.model in ['add', 'concat']:
            pos_input = K.tile(K.expand_dims(K.arange(0, seq_len), axis=0), [batch_size, 1])
        else:
            pos_input = inputs
        pos_input = K.cast(pos_input, K.floatx())
        evens = K.arange(0, output_dim // 2) * 2
        odds = K.arange(0, output_dim // 2) * 2 + 1
        sim_embed = K.sin(
            K.dot(
                K.expand_dims(pos_input, -1),
                K.expand_dims(1.0 / K.pow(
                    10000.0,
                    K.cast(evens, K.floatx()) / K.cast(output_dim, K.floatx())
                ), 0)
            )
        )
        cos_embed = K.cos(
            K.dot(
                K.expand_dims(pos_input, -1),
                K.expand_dims(1.0 / K.pow(
                    10000.0, K.cast((odds - 1), K.floatx()) / K.cast(output_dim, K.floatx())
                ), 0)
            )
        )
        embed = K.stack([sim_embed, cos_embed], axis=-1)
        output = K.reshape(embed, [-1, seq_len, output_dim])
        if self.mode == 'add':
            output += inputs
        elif self.mode == 'concat':
            output = K.concatenate([inputs, output], axis=-1)
        return output
