import numpy as np
from genevis.render import RaycastRenderer
from genevis.transfer_function import TFColor
from volume.volume import GradientVolume, Volume
from collections.abc import ValuesView
from tqdm import tqdm
import math


def get_voxel(volume: Volume, x: float, y: float, z: float):
    """
    Retrieves the value of a voxel for the given coordinates.
    :param volume: Volume from which the voxel will be retrieved.
    :param x: X coordinate of the voxel
    :param y: Y coordinate of the voxel
    :param z: Z coordinate of the voxel
    :return: Voxel value
    """
    if x < 0 or y < 0 or z < 0 or x >= volume.dim_x - 1 or y >= volume.dim_y - 1 or z >= volume.dim_z - 1 :
        return 0

    """
    (v0, ..., v7) nearest voxels to [x,y,z] 
       v6--------v7
      /|        /|
     / |       / |
    v4--------v5 |
    |  |      |  |
    |  v2-----|--v3
    | /       | /
    |/        |/
    v0--------v1
    """
    # get voxel coordinates limits     x0-------x-------------x1
    x0 = math.floor(x)
    y0 = math.floor(y)
    z0 = math.floor(z)
    x1 = math.ceil(x)
    y1 = math.ceil(y)
    z1 = math.ceil(z)

    # compute voxels
    v0 = volume.data[x0, y0, z0] 
    v1 = volume.data[x1, y0, z0]
    v2 = volume.data[x0, y0, z1]
    v3 = volume.data[x1, y0, z1]
    v4 = volume.data[x0, y1, z0]
    v5 = volume.data[x1, y1, z0]
    v6 = volume.data[x0, y1, z1]
    v7 = volume.data[x1, y1, z1]

    # compute parameters
    alpha = x - x0
    beta = y - y0
    gamma = z - z0

    return  (1-alpha)*(1-beta)*(1-gamma)*v0 + \
            alpha*(1-beta)*(1-gamma)*v1 + \
            (1-alpha)*beta*(1-gamma)*v2 + \
            alpha*beta*(1-gamma)*v3 + \
            (1-alpha)*(1-beta)*gamma*v4 + \
            alpha*(1-beta)*gamma*v5 + \
            (1-alpha)*beta*gamma*v6 + \
            alpha*beta*gamma*v7

class RaycastRendererImplementation(RaycastRenderer):
    """
    Class to be implemented.
    """

    def clear_image(self):
        """Clears the image data"""
        self.image.fill(0)

    def render_slicer(self, view_matrix: np.ndarray, volume: Volume, image_size: int, image: np.ndarray):
        # Clear the image
        self.clear_image()

        # U vector. See documentation in parent's class
        u_vector = view_matrix[0:3]

        # V vector. See documentation in parent's class
        v_vector = view_matrix[4:7]

        # View vector. See documentation in parent's class
        view_vector = view_matrix[8:11]

        # Center of the image. Image is squared
        image_center = image_size / 2

        # Center of the volume (3-dimensional)
        volume_center = [volume.dim_x / 2, volume.dim_y / 2, volume.dim_z / 2]
        volume_maximum = volume.get_maximum()

        # Define a step size to make the loop faster
        step = 10 if self.interactive_mode else 1

        for i in range(0, image_size, step):
            for j in range(0, image_size, step):
                # Get the voxel coordinate X
                voxel_coordinate_x = u_vector[0] * (i - image_center) + v_vector[0] * (j - image_center) + \
                                     volume_center[0]

                # Get the voxel coordinate Y
                voxel_coordinate_y = u_vector[1] * (i - image_center) + v_vector[1] * (j - image_center) + \
                                     volume_center[1]

                # Get the voxel coordinate Z
                voxel_coordinate_z = u_vector[2] * (i - image_center) + v_vector[2] * (j - image_center) + \
                                     volume_center[2]

                # Get voxel value
                value = get_voxel(volume, voxel_coordinate_x, voxel_coordinate_y, voxel_coordinate_z)

                # Normalize value to be between 0 and 1
                red = value / volume_maximum
                green = red
                blue = red
                alpha = 1.0 if red > 0 else 0.0

                # Compute the color value (0...255)
                red = math.floor(red * 255) if red < 255 else 255
                green = math.floor(green * 255) if green < 255 else 255
                blue = math.floor(blue * 255) if blue < 255 else 255
                alpha = math.floor(alpha * 255) if alpha < 255 else 255

                # Assign color to the pixel i, j
                image[(j * image_size + i) * 4] = red
                image[(j * image_size + i) * 4 + 1] = green
                image[(j * image_size + i) * 4 + 2] = blue
                image[(j * image_size + i) * 4 + 3] = alpha

    def render_mip(self, view_matrix: np.ndarray, volume: Volume, image_size: int, image: np.ndarray):
        # Clear the image
        self.clear_image()

        # ration vectors
        u_vector = view_matrix[0:3] # X
        v_vector = view_matrix[4:7] # Y
        view_vector = view_matrix[8:11] # Z

        # Center of the image. Image is squared
        image_center = image_size / 2

        # Center of the volume (3-dimensional)
        volume_center = [volume.dim_x / 2, volume.dim_y / 2, volume.dim_z / 2]
        volume_maximum = volume.get_maximum()
        
        # Diagonal cube
        diagonal = math.floor(math.sqrt(volume.dim_x**2 + volume.dim_y**2 + volume.dim_z**2) / 2)

        # Define a step size to make the loop faster
        step = 10 if self.interactive_mode else 1

        for i in tqdm(range(0, image_size, step), desc='render', leave=False):
            for j in range(0, image_size, step):
                
                value = 0
                for z in range(-diagonal, diagonal, 2):
                    # Get the voxel coordinate X
                    voxel_coordinate_x = u_vector[0] * (i - image_center) + v_vector[0] * (j - image_center) \
                                        + view_vector[0] * z + volume_center[0]

                    # Get the voxel coordinate Y
                    voxel_coordinate_y = u_vector[1] * (i - image_center) + v_vector[1] * (j - image_center) \
                                        + view_vector[1] * z + volume_center[1]

                    # Get the voxel coordinate Z
                    voxel_coordinate_z = u_vector[2] * (i - image_center) + v_vector[2] * (j - image_center) \
                                        + view_vector[2] * z + volume_center[2]

                    # Get voxel value
                    tmp = get_voxel(volume, voxel_coordinate_x, voxel_coordinate_y, voxel_coordinate_z)
                    value = tmp if value < tmp else value

                # Normalize value to be between 0 and 1
                red = value / volume_maximum
                green = red
                blue = red
                alpha = 1.0 if red > 0 else 0.0

                # Compute the color value (0...255)
                red = math.floor(red * 255) if red < 255 else 255
                green = math.floor(green * 255) if green < 255 else 255
                blue = math.floor(blue * 255) if blue < 255 else 255
                alpha = math.floor(alpha * 255) if alpha < 255 else 255

                # Assign color to the pixel i, j
                image[(j * image_size + i) * 4] = red
                image[(j * image_size + i) * 4 + 1] = green
                image[(j * image_size + i) * 4 + 2] = blue
                image[(j * image_size + i) * 4 + 3] = alpha

    def render_compositing(self, view_matrix: np.ndarray, volume: Volume, image_size: int, image: np.ndarray):
        # Clear the image
        self.clear_image()
        
        # ration vectors
        u_vector = view_matrix[0:3] # X
        v_vector = view_matrix[4:7] # Y
        view_vector = view_matrix[8:11] # Z

        # Center of the image. Image is squared
        image_center = image_size / 2

        # Center of the volume (3-dimensional)
        volume_center = [volume.dim_x / 2, volume.dim_y / 2, volume.dim_z / 2]
        diagonal = math.floor(math.sqrt(volume.dim_x**2 + volume.dim_y**2 + volume.dim_z**2) / 2)

        # Define a step size to make the loop faster
        step = 10 if self.interactive_mode else 1

        for i in tqdm(range(0, image_size, step), desc='render', leave=False):
            for j in range(0, image_size, step):

                last_color: TFColor = None
                for z in range(diagonal, -diagonal, -2):
                    # Get the voxel coordinate X
                    voxel_coordinate_x = u_vector[0] * (i - image_center) + v_vector[0] * (j - image_center) \
                                        + view_vector[0] * z + volume_center[0]

                    # Get the voxel coordinate Y
                    voxel_coordinate_y = u_vector[1] * (i - image_center) + v_vector[1] * (j - image_center) \
                                        + view_vector[1] * z + volume_center[1]

                    # Get the voxel coordinate Z
                    voxel_coordinate_z = u_vector[2] * (i - image_center) + v_vector[2] * (j - image_center) \
                                        + view_vector[2] * z + volume_center[2]

                    # Get voxel value
                    value = get_voxel(volume, voxel_coordinate_x, voxel_coordinate_y, voxel_coordinate_z)
                    value = round(value)
                    
                    # Get voxel RGBA
                    base_color = self.tfunc.get_color(value)
                    voxel_color = TFColor(base_color.r*base_color.a, base_color.g*base_color.a, \
                                          base_color.b*base_color.a, base_color.a)
                    if last_color != None:
                        r = voxel_color.r + (1 - voxel_color.a)*last_color.r
                        g = voxel_color.g + (1 - voxel_color.a)*last_color.g
                        b = voxel_color.b + (1 - voxel_color.a)*last_color.b
                        voxel_color = TFColor(r, g, b, 1.0)
                    
                    last_color = voxel_color

                # Normalize value to be between 0 and 1
                red = last_color.r
                green = last_color.g
                blue = last_color.b
                alpha = last_color.a if red > 0 and green > 0 and blue > 0 else 0.0

                # Compute the color value (0...255)
                red = math.floor(red * 255) if red < 255 else 255
                green = math.floor(green * 255) if green < 255 else 255
                blue = math.floor(blue * 255) if blue < 255 else 255
                alpha = math.floor(alpha * 255) if alpha < 255 else 255

                # Assign color to the pixel i, j
                image[(j * image_size + i) * 4] = red
                image[(j * image_size + i) * 4 + 1] = green
                image[(j * image_size + i) * 4 + 2] = blue
                image[(j * image_size + i) * 4 + 3] = alpha

    def render_mouse_brain(self, view_matrix: np.ndarray, annotation_volume: Volume, energy_volumes: dict,
                           image_size: int, image: np.ndarray):
        """
        fucntion that implements the visualization of the mouse brain.
        select below the function that you want in order to visualize the data.
        """
        # create volume for the gradient magnitude
        magnitude_volume = np.zeros(annotation_volume.data.shape)
        for x in range(0, annotation_volume.dim_x):
            for y in range(0, annotation_volume.dim_y):
                for z in range(0, annotation_volume.dim_z):
                    magnitude_volume[x, y, z] = self.annotation_gradient_volume.get_gradient(x, y, z).magnitude
        magnitude_volume = Volume(magnitude_volume)
        
        # set internal transfer function for borders
        self.tfunc.init(0, round(self.annotation_gradient_volume.get_max_gradient_magnitude()))

        # set of different functions
        self.visualize_annotations_only(view_matrix, annotation_volume, magnitude_volume, image_size, image, csv_colors=False, precision=1)
    

    def visualize_annotations_only(self, view_matrix: np.ndarray, annotation_volume: Volume, magnitude_volume: Volume,
                           image_size: int, image: np.ndarray, csv_colors: bool = False, precision = 1):

        # Clear the image
        self.clear_image()

        # rotation vectors
        u_vector = view_matrix[0:3]     # X
        v_vector = view_matrix[4:7]     # Y
        view_vector = view_matrix[8:11] # Z

        # image and volume in the center of the window
        image_center = image_size / 2
        volume_center = [annotation_volume.dim_x / 2, annotation_volume.dim_y / 2, annotation_volume.dim_z / 2]
        half_diagonal = math.floor(math.sqrt(annotation_volume.dim_x**2 + annotation_volume.dim_y**2 + annotation_volume.dim_z**2) / 2)

        # Define a step size to make the loop faster
        step = 20 if self.interactive_mode else 1
        for i in tqdm(range(0, image_size, step), desc='render', leave=False):
            for j in range(0, image_size, step):

                last_color: TFColor = None
                for k in range(half_diagonal, -half_diagonal, -precision):

                    # Get the rotated voxel value
                    x = u_vector[0] * (i - image_center) + v_vector[0] * (j - image_center) + view_vector[0] * k + volume_center[0]
                    y = u_vector[1] * (i - image_center) + v_vector[1] * (j - image_center) + view_vector[1] * k + volume_center[1]
                    z = u_vector[2] * (i - image_center) + v_vector[2] * (j - image_center) + view_vector[2] * k + volume_center[2]
                    value = get_voxel(magnitude_volume, x, y, z)

                    # compute color
                    if value != 0:
                        voxel_color: TFColor = self.tfunc.get_color(round(value)) # <- check round
                        voxel_color = TFColor(voxel_color.r*voxel_color.a, voxel_color.g*voxel_color.a, \
                                            voxel_color.b*voxel_color.a, voxel_color.a) 
                        if last_color != None:
                            voxel_color = TFColor(voxel_color.r + last_color.r*(1-voxel_color.a), \
                                                voxel_color.g + last_color.g*(1-voxel_color.a), \
                                                voxel_color.b + last_color.b*(1-voxel_color.a), \
                                                1.0)
                        last_color = voxel_color

                # Select RGB values
                if last_color == None:
                    red = 0.0
                    green = 0.0
                    blue = 0.0
                    alpha = 0.0
                else:
                    red = last_color.r
                    green = last_color.g
                    blue = last_color.b
                    alpha = last_color.a if red > 0 and green > 0 and blue > 0 else 0.0

                # Compute the color value (0...255)
                red = math.floor(red * 255) if red < 255 else 255
                green = math.floor(green * 255) if green < 255 else 255
                blue = math.floor(blue * 255) if blue < 255 else 255
                alpha = math.floor(alpha * 255) if alpha < 255 else 255

                # Assign color to the pixel i, j
                image[(j * image_size + i) * 4] = red
                image[(j * image_size + i) * 4 + 1] = green
                image[(j * image_size + i) * 4 + 2] = blue
                image[(j * image_size + i) * 4 + 3] = alpha                 
