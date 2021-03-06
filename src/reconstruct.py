import numpy as np
import scipy.signal
import librosa

def get_GEVD(Mask_s, mix_sig, fft_size, hop_size):
    #Mask_s,Mask_n, mix are all of size (#time, #freq,4)
    #output MWF (freq,4), speech and noise ()
    Mask_s = Mask_s.T
    Mask_n=1-Mask_s
    T_clip = Mask_s.shape[1] # clip to mask to lazily account for truncation when using librosa.util.frame
    mix_w = librosa.stft(mix_sig[0,:], n_fft=fft_size, hop_length=hop_size, window='hann')[:, :T_clip]
    mix_x = librosa.stft(mix_sig[1,:], n_fft=fft_size, hop_length=hop_size, window='hann')[:, :T_clip]
    mix_y = librosa.stft(mix_sig[2,:], n_fft=fft_size, hop_length=hop_size, window='hann')[:, :T_clip]
    mix_z = librosa.stft(mix_sig[3,:], n_fft=fft_size, hop_length=hop_size, window='hann')[:, :T_clip]
    mix = np.stack((mix_w,mix_x,mix_y,mix_z), axis=2)

    s_bar=Mask_s[:,:,None]*mix#pointwise multiplication (#time,#freq,4)
    F,T=s_bar.shape[0:2]
    phi_ss=(1.0/T)*np.sum(s_bar[:,:,np.newaxis,:]*s_bar[:,:,:,np.newaxis].conj(),axis=1).real#should be of (#freq,4,4)

    sn_bar=Mask_n[:,:,None]*mix
    Tn,Fn=sn_bar.shape[0:2]
    phi_nn=1/Tn*np.sum(sn_bar[:,:,np.newaxis,:]*sn_bar[:,:,:,np.newaxis].conj(),axis=1).real#(#freq,4,4)

    #rank-1 approximation
    u1=np.zeros((phi_nn.shape[1],))
    u1[0]=1
    phi_interm=np.zeros((F,4,4))
    phi_ss_r1=np.zeros((F,4,4))
    wGEVD=np.zeros((F,4))

    for i in range(Fn):
        phi_interm[i,:,:]=np.linalg.lstsq(phi_nn[i,:,:],phi_ss[i,:,:], rcond=None)[0]#(#freq,4,4)
        u,s,v=np.linalg.svd(phi_interm[i,:,:], full_matrices=False)
        eig=np.argmax(s)
        phi_ss_r1[i,:,:]=s[eig] * np.outer(u[:,eig], v[eig,:])
        wGEVD[i,:]=np.dot(np.linalg.lstsq(phi_ss_r1[i,:,:]+phi_nn[i,:,:],phi_ss_r1[i,:,:], rcond=None)[0], u1)#(#freq,4)

    #get wGEVD
    speech_sp=np.sum(wGEVD[:,None,:]*mix[:,:,:],axis=2)
    speech_sig=librosa.istft(speech_sp)

    return speech_sig
