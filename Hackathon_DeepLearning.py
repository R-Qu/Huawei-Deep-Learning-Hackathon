# -*- coding: utf-8 -*-
"""SSL.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1uH7DXDiBqOINqCxse38ZxnCPJdkozqHF
"""

import tensorflow as tf
from tensorflow.python.keras.models import Sequential, Model
from tensorflow.python.keras.layers import Dense, Dropout, Flatten, Input, Conv2D, MaxPool2D, Activation, BatchNormalization, GlobalMaxPool2D, UpSampling2D, Conv2DTranspose, Lambda, Reshape
from tensorflow.python.keras.datasets import cifar10, mnist
from tensorflow.python.keras import backend as K
from tensorflow.python.keras.optimizers import Adam
from tensorflow.python.keras import metrics
from tensorflow.python.keras.utils import to_categorical

import matplotlib.pyplot as plt

(x_train, y_train), (x_test, y_test) = cifar10.load_data()
# (x_train, y_train), (x_test, y_test) = mnist.load_data()

x_train = x_train / 255.
x_test = x_test / 255.

# x_train = x_train.reshape((-1, 28, 28, 1))

batch_size = 250
latent_dim = 512
intermediate_dim = 512
epsilon_std = 1.0
epochs = 1000
activation = 'relu'
dropout = 0.2
learning_rate = 0.0001
decay = 0.0

img_rows, img_cols, img_chns = 32, 32, 3
# img_rows, img_cols, img_chns = 28, 28, 1

if K.image_data_format() == 'channels_first':
    original_img_size = (img_chns, img_rows, img_cols)
else:
    original_img_size = (img_rows, img_cols, img_chns)


def create_enc_conv_layers(stage, **kwargs):
    conv_name = '_'.join(['enc_conv', str(stage)])
    bn_name = '_'.join(['enc_bn', str(stage)])
    layers = [
        Conv2D(name=conv_name, **kwargs),
        BatchNormalization(name=bn_name),
        Activation(activation),
    ]
    return layers

def create_dense_layers(stage, width):
    dense_name = '_'.join(['enc_dense', str(stage)])
    bn_name = '_'.join(['enc_bn', str(stage)])
    layers = [
        Dense(width, name=dense_name),
        BatchNormalization(name=bn_name),
        Activation(activation),
        Dropout(dropout),
    ]
    return layers

def create_head_layers(stage, width):
    dense_name = '_'.join(['enc_head', str(stage)])
    bn_name = '_'.join(['enc_bn', str(stage)])
    layers = [
        Dense(width, name=dense_name),
        Activation('softmax')
    ]
    return layers

def inst_layers(layers, in_layer):
    x = in_layer
    for layer in layers:
        if isinstance(layer, list):
            x = inst_layers(layer, x)
        else:
            x = layer(x)
        
    return x

def create_dec_trans_conv_layers(stage, **kwargs):
    conv_name = '_'.join(['dec_trans_conv', str(stage)])
    bn_name = '_'.join(['dec_bn', str(stage)])
    layers = [
        Conv2DTranspose(name=conv_name, **kwargs),
        BatchNormalization(name=bn_name),
        Activation(activation),
    ]
    return layers

def sampling(args, batch_size=batch_size, latent_dim=latent_dim, epsilon_std=epsilon_std):
    z_mean, z_log_var = args
    
    epsilon = K.random_normal(shape=(batch_size, latent_dim),
                              mean=0., stddev=epsilon_std)
    
    return z_mean + K.exp(z_log_var) * epsilon

def kl_loss(x, x_decoded_mean):
    kl_loss = - 0.5 * K.sum(1. + z_log_var - K.square(z_mean) - K.exp(z_log_var), axis=-1)
   
    return K.mean(kl_loss)

def logx_loss(x, x_decoded_mean):
    x = K.flatten(x)
    x_decoded_mean = K.flatten(x_decoded_mean)
    xent_loss = img_rows * img_cols * img_chns * metrics.binary_crossentropy(x, x_decoded_mean)
    return xent_loss

# def vae_loss(x, x_decoded_mean, beta=1):
#     return logx_loss(x, x_decoded_mean) + beta * kl_loss(x, x_decoded_mean)

# def get_loss(beta):
#     return lambda x, x_decoded: vae_loss(x, x_decoded, beta)

enc_filters=128

enc_layers = [
    create_enc_conv_layers(stage=1, filters=enc_filters, kernel_size=3, strides=2, padding='same'),
    create_enc_conv_layers(stage=2, filters=enc_filters // 2, kernel_size=3, strides=2, padding='same'),
#     create_enc_conv_layers(stage=3, filters=enc_filters // 4, kernel_size=3, strides=2, padding='same'),
    Flatten(),
    create_dense_layers(stage=4, width=intermediate_dim),
]

x = Input(shape=original_img_size)
enc_dense = inst_layers(enc_layers, x)

z_mean = Dense(latent_dim)(enc_dense)
# z_log_var = Dense(latent_dim)(enc_dense)

z = z_mean #Lambda(sampling, output_shape=(latent_dim,))([z_mean, z_log_var])

dec_filters = 128
decoder_layers = [
    create_dense_layers(stage=10, width=intermediate_dim),
    Reshape((8, 8, intermediate_dim // 64)),
    create_dec_trans_conv_layers(11, filters=dec_filters, kernel_size=3, strides=2, padding='same'),
    create_dec_trans_conv_layers(12, filters=dec_filters // 2, kernel_size=3, strides=2, padding='same'),
#     create_dec_trans_conv_layers(13, filters=dec_filters // 4, kernel_size=3, strides=2, padding='same'),
    Conv2DTranspose(name='x_decoded', filters=3, kernel_size=1, strides=1, activation='sigmoid'),
]

output = inst_layers(decoder_layers, z)

vae = Model(inputs=x, outputs=output)
# optimizer = Adam(lr=learning_rate, decay=decay)
vae.compile(optimizer='adam', loss='mse')

vae.summary()

history = vae.fit(x_train, x_train, batch_size=batch_size, epochs=20)

pred = vae.predict(x_train[:250], batch_size=250)

i = 2
plt.imshow(x_train[i])
plt.grid(False)
plt.show()
plt.imshow(pred[i])
plt.grid(False)
plt.show()

from sklearn.decomposition import PCA
pca = PCA(250)
x_train_flat = x_train.reshape((-1, 32*32*3))
x_train_pca = pca.fit_transform(x_train_flat)

rec_train = pca.inverse_transform(x_train_pca)
rec_imgs = rec_train.reshape((-1, 32, 32, 3)).clip(0, 0.999)

plt.imshow(rec_imgs[2])
plt.grid(False)
plt.show()

classifier_layers = [
    create_dense_layers(21, 50),
    create_head_layers(22, 10)
]

class_pred = inst_layers(classifier_layers, z_mean)

classifier = Model(inputs=x, outputs=class_pred)

for layer in classifier.layers[:-6]:
    layer.trainable = False

classifier.summary()

x_label, y_label = x_test[:5000], y_test[:5000]
x_val, y_val = x_test[5000:], y_test[5000:]

y_label = to_categorical(y_label)
y_val = to_categorical(y_val)

classifier.compile(optimizer='adadelta', loss='categorical_crossentropy', metrics=['accuracy'])

classifier.fit(x_label, y_label, batch_size=1000, epochs=1000, validation_data=(x_val, y_val))