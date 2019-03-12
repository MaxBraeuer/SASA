import numpy as np
from star_product import *
from smat_oparations import *

class Layer:
    def __init__(self):
        self.mirror_bool = False
        self.flip_bool = False
        self.angle = 0

    def flip(self):
        self.flip_bool = True
        return

    def mirror(self):
        self.mirror_bool = True

    def rotate(self, angle):
        self.angle = angle



class MetaLayer(Layer):
    def __init__(self, s_mat, cladding, substrate):
        Layer.__init__(self)
        self.s_mat = s_mat
        self.cladding = cladding
        self.substrate = substrate

class NonMetaLayer(Layer):
    """
    Parameters
    ----------
    wav_vec : vector of the measured wavelengths
    height : height in (μm)
    n_vec : one or two vactors containing the diffraction indeces
            if one vector is given homogenous behavior will be assumed
    """
    def __init__(self, height, *n_vec):
        Layer.__init__(self)
        self.height = height
        self.height_len = np.size(self.height)
        self.n_x = n_vec[0]
        #isotropic material
        if len(n_vec) == 1:
            self.n_y = self.n_x
        #anisotropic material
        elif len(n_vec) == 2:
            self.n_y = n_vec[1]
        else:
            raise ValueError("input 1 or 2 refrectiv index vectors")



class Stack:
    """
    Parameters
    ----------
    layer_list : list of Layer objects
    cladding : float / vector
               The refrectiv Index of the material on top of the stack
               if the input is a single float n_i wavelength independent
               behavior will be assumed.
    substrate : float / vectors
                The refractiv index of the material below the stack

    """
    def __init__(self, layer_list, wav_vec, cladding, substrate):

        self.layer_list = layer_list
        self.cladding = cladding
        self.substrate = substrate
        self.wav_vec = wav_vec
        self.wav_vec_len = len(self.wav_vec)

    def create_propagator(self, nml):
        """
        Creates the propergator S-Matrix of a Non-Meta-Layers

        Parameters
        ----------
        nml: NonMetaLayer object
        """

        #Height is a scalar
        if nml.height_len == 1:
            nml.height = np.array([nml.height])

        s_mat_list = np.zeros((nml.height_len, self.wav_vec_len,4,4)).astype(complex)
        for i in range(nml.height_len):
            prop_x = np.exp(1j * nml.n_x * nml.height[i] * 2*np.pi /self.wav_vec)
            prop_y = np.exp(1j * nml.n_y * nml.height[i] * 2*np.pi /self.wav_vec)
            s_mat_list[i,:,0,0] = prop_x
            s_mat_list[i,:,1,1] = prop_y
            s_mat_list[i,:,2,2] = prop_x
            s_mat_list[i,:,3,3] = prop_y

        s_mat = np.squeeze(s_mat_list)
        #apply symmetry opperations
        if nml.mirror_bool:
            s_mat = array_mirror_smat(s_mat)
        if nml.flip_bool:
            s_mat = array_flip_smat(s_mat)
        if nml.angle != 0:
            s_mat = array_rot_smat(s_mat, nml.angle)

        return s_mat

    def create_interface(self, l_2, l_1):
        """
        Creates the interface S-Matrix for the transmission between 2 Non-Meta-Layers

        Parameters
        ----------
        l_1 , l_2:  NonMetaLayer or MetaLayer Objects
        """

        #load n_* from the Layers
        if (type(l_1) is NonMetaLayer):
            n1_x = l_1.n_x
            n1_y = l_1.n_y
        else:
            n1_x = l_1.substrate
            n1_y = l_1.substrate

        if(type(l_2) is NonMetaLayer) :
            n2_x = l_2.n_x
            n2_y = l_2.n_y
        else:
            n2_x = l_2.cladding
            n2_y = l_2.cladding

        #transmission and reflection in x and y direction

        s_mat_list = np.zeros((self.wav_vec_len,4,4)).astype(complex)
        #Transmission
        s_mat_list[:,0,0] = 2*n1_x/(n1_x + n2_x)
        s_mat_list[:,1,1] = 2*n1_y/(n1_y + n2_y)
        s_mat_list[:,2,2] = 2*n2_x/(n1_x + n2_x)
        s_mat_list[:,3,3] = 2*n2_y/(n1_y + n2_y)
        #Reflection
        R_x = (n1_x - n2_x)/(n1_x + n2_x)
        R_y = (n1_y - n2_y)/(n1_y + n2_y)
        s_mat_list[:,0,2] = R_x
        s_mat_list[:,1,3] = R_y
        s_mat_list[:,2,0] = -1*R_x
        s_mat_list[:,3,1] = -1*R_y
        """
        This Operrator is constructed:
        [T_x  , 0    , R_x,    0],
        [ 0   , T_y  ,   0,  R_y],
        [-1*R_x, 0   , T_x,  0  ],
        [ 0    ,-1*R_y, 0  , T_y ]
        """
        #apply symmetry opperations


        return s_mat_list

    def create_interface_rot(self, l_2, l_1):
        """
        Creates the interface S-Matrix for the transmission between
        2 Non-Meta-Layers in case of rotation

        Parameters
        ----------
        l_1 , l_2:  NonMetaLayer or MetaLayer Objects
        """
        vacuum_layer = NonMetaLayer(0, np.ones(self.wav_vec_len))
        s_mat1 = self.create_interface(vacuum_layer, l_2)
        s_mat2 = self.create_interface(l_1, vacuum_layer)
        s_mat = starProductanalyt(array_rot_smat(s_mat1, l_2.angle),
                                  array_rot_smat(s_mat2, l_1.angle))
        return  s_mat



    def build(self):
        """
        Build all the propagation and interface matrices and multiplies them.

        Returns
        -------
        s_mat : Lx4x4 S-matrix describing the whole stack
        """

        #Create Layer-Object for the cladding
        clad_layer = NonMetaLayer(None, self.cladding)
        #Create Layer-Object for the substrate
        subs_layer = NonMetaLayer(None, self.substrate)
        #add the substrate layer to the back
        self.layer_list.append(subs_layer)
        #create interface between the cladding and the first layer
        inter = self.create_interface(clad_layer, self.layer_list[0])
        s_mat_list = [inter]
        for i in range(len(self.layer_list) - 1):

            current_layer = self.layer_list[i]
            next_layer = self.layer_list[i+1]

            if type(current_layer) is NonMetaLayer:
                prop = self.create_propagator(current_layer)

            elif type(current_layer) is MetaLayer:
                prop = array_rot_smat(current_layer.s_mat,current_layer.angle)


            else:
                raise ValueError("Stack has to consist of Mata and \
                                NonMetaLayers")
            #This can be further optimized by a better differentiation between
            #the cases
            if (current_layer.angle != 0) or (next_layer.angle != 0):
                inter = self.create_interface_rot(current_layer, next_layer)
            else:
                inter = self.create_interface(current_layer, next_layer)
            s_mat_list.append(prop)
            s_mat_list.append(inter)
        #end building loop

        return starProduct_Cascaded(s_mat_list)
