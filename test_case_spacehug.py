# Test case for JetStyle; Exec.: Dmitri Y. Lapshin
from PIL import Image, ImageDraw, ImageFont
import argparse
import json
import logging
import timeit

__VERSION__ = '0.0.1'
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d.%m.%Y %H:%M:%S', level=logging.INFO)
logger = logging.getLogger(__name__)


class Map:
    """
    Constucts a map of applications from given amount
    Builds json-matrix
    Outputs an image based off the json-matrix in jpeg format
    """

    def __init__(self, applications_amount):
        """
        Initializes the map
        """
        # Given the initial dimensions (196, 98, 350):
        self.large_horisontal = 350.0                                # Object (house) dimensions
        self.large_half_horisontal = 175.0                           #
        self.large_vertical = 175.0                                  #
        self.large_half_vertical = 87.5                              #
        self.small_horisontal = 175.0                                # Gap dimensions
        self.small_vertical = 87.5                                   #
        self.chunk_horisontal = 1750.0                               # Chunk (block of houses) dimensions
        self.chunk_half_horisontal = 875.0                           #
        self.chunk_vertical = 875.0                                  #
        self.chunk_half_vertical = 437.5                             #
        self.chunk_center_coordinate = [875.0, 437.5]                # Chunk (block of houses) center
        self.array_size = 0
        self.array_center = [0, 0]
        self.coordinates_delta = []
        self.map = []
        self.apps_coordinates = {}
        self.canvas_dimensions = []
        self.json_data = {}
        self.applications_amount = applications_amount                # Data from command line '-a'
        self.applications = list(range(1, applications_amount + 1))   # The list of applications to arrange
        self.chunk_size = 12                                          # Amount of applications per chunk
        self.chunks = list(self.split_applications())                 # Applications arranged by chunk
        self.chunks_structure = list(self.split_applications())       # Applications arranged by chunk and parity
        self.chunks_amount = len(self.chunks)                         # Total amount of chunks

    def __repr__(self):

        return f'Blocks: {self.chunks_amount}\n' \
               f'Array size: {self.array_size} x {self.array_size}\n' \
               f'Array center coordinates: {self.array_center}\n' \
               f'Chunks map: {self.map}\n' \
               f'Objects map: {self.chunks_structure}'

    def split_applications(self):
        """
        Yield successive chunk_size-sized chunks from applications
        """
        apps = self.applications[:]                                   # Blind-copying the list, not referencing it
        for position in range(0, len(apps), self.chunk_size):         # Splitting the list to even-sized chunks
            result = apps[position:position + self.chunk_size]

            if len(result) == 12:
                yield result

            else:
                yield result + [0] * (self.chunk_size - len(result))  # Fills the rest of chunk with zeroes

    def get_array_size(self):
        """
        Figures out what the chunk map square side is, we need it for parity calculation later on
        """
        chunks_count = self.chunks_amount - 1                         # We need to subtract 1 so no excessive space is
        k = 0                                                         # created in the map (i.e. no zero-border)

        while chunks_count > 0:
            k += 1
            chunks_count -= 6 * k

        self.array_size = 2 * k + 1

    def locate_array_center(self):
        """
        Figures out the coordinates of center of chunks map array to start building chunks around it
        """
        coordinate = self.array_size // 2
        self.array_center = [coordinate, coordinate]

    def get_coordinates_delta(self):
        """
        Calculates coordinates delta for each chunk in relation to the previous chunk,
        so we can build a chunks map like this:

        [0, 0, 19, 8, 9]
        [0, 18, 7, 2, 10]
        [17, 6, 1, 3, 11]
        [16, 5, 4, 12, 0]
        [15, 14, 13, 0, 0]

        """
        x = [0]                                                       # X differs from Y coordinate delta for the first
        x_ones = 1                                                    # two elements, along with different order
        x_zeroes = 1                                                  # That is due to the order the chunks are placed
        y = [0, -1]                                                   # in
        y_ones = 2                                                    #
        y_zeroes = 1                                                  #

        while len(x) <= self.chunks_amount:
            x += ([1] * x_ones + [0] * x_zeroes + [-1] * (x_ones + 1) + [0] * x_zeroes)
            x_ones += 2
            x_zeroes += 1

        while len(y) <= self.chunks_amount:
            y += ([1] * y_ones + [0] * y_zeroes + [-1] * (y_ones + 1) + [0] * y_zeroes)
            y_ones += 2
            y_zeroes += 1

        self.coordinates_delta = [delta for delta in zip(x[:self.chunks_amount], y[:self.chunks_amount])]

    def fill_chunks_map(self):
        """
        Fills the map with chunk's IDs
        """
        # Time to prearrange template for chunks
        self.map = [[0] * self.array_size for _ in range(self.array_size)]
        x, y = self.array_center

        # Filling the map using deltas we get earlier in get_coordinates_delta()
        for chunk, (dx, dy) in zip(range(self.chunks_amount), self.coordinates_delta):
            x += dx
            y += dy
            self.map[y][x] = chunk + 1

    def chunk_is_odd(self, chunk_number):
        """
        Figures out whether the chunk is odd (and the applications in it should be in "reversed" order) or not
        """
        for idx, value in enumerate(item for line in self.map for item in line):

            # If number of chunk is not even and the chunk is not zero (there is no "zero" chunks)
            if not idx % 2 and value == chunk_number:
                return True

            elif value and value == chunk_number:
                return False

    def chunk_shift(self, delta):
        """
        Figures out how to shift chunk center coordinate to place applications later on
        """
        # Since there is only 6 possible ways to shift coordinates in the hexagonal spiral design (permutation of
        # -1, 0 and 1 without repetition can produce only 6 different tuples):

        # straight right shift
        if delta == (1, -1):
            return [self.chunk_horisontal - self.small_horisontal, 0]

        # down-left shift
        elif delta == (0, 1):
            return [- self.chunk_half_horisontal + self.small_horisontal * 0.5,
                    self.chunk_half_vertical - self.small_vertical * 0.5]

        # straight left shift
        elif delta == (-1, 1):
            return [- self.chunk_horisontal + self.small_horisontal, 0]

        # up-left shift
        elif delta == (-1, 0):
            return [- self.chunk_half_horisontal + self.small_horisontal * 0.5,
                    - self.chunk_half_vertical + self.small_vertical * 0.5]

        # up-right shift
        elif delta == (0, -1):
            return [self.chunk_half_horisontal - self.small_horisontal * 0.5,
                    - self.chunk_half_vertical + self.small_vertical * 0.5]

        # down-right shift
        elif delta == (1, 0):
            return [self.chunk_half_horisontal - self.small_horisontal * 0.5,
                    self.chunk_half_vertical - self.small_vertical * 0.5]

        # No shift for the first chunk
        else:
            return [0, 0]

    def place_applications(self):
        """
        Arranges all given applications in chunks depending on parity and maps coordinates
        """
        point_coordinates = {}
        # Define chunk start to shift it later after all the apps in particular chunk are placed
        chunk_start = self.chunk_center_coordinate

        for chunk_number, chunk in enumerate(self.chunks):
            # Prepare the template for applications in chunk
            pattern = [[0] * 4 for _ in range(3)]
            # Reversed to pop() it later
            items_to_place = chunk[::-1]
            # Figure out the shift
            chunks_shift = self.chunk_shift(self.coordinates_delta[chunk_number])

            # Given that chunks change their directions
            if self.chunk_is_odd(chunk_number + 1):
                # The shift in relation to chunk center
                start_shift = [0, -3 * self.small_vertical]
                # The shift of app in relation to previous app
                shift = [- self.small_horisontal, self.small_vertical]
                # Shift of app in relation to row
                row_shift = [4.5 * self.small_horisontal, - 1.5 * self.small_vertical, ]
            # Chunk number is even:
            else:
                # The shift in relation to chunk center
                start_shift = [0, -3 * self.small_vertical]
                # The shift of app in relation to previous app
                shift = [self.small_horisontal, self.small_vertical]
                # Shift of app in relation to row
                row_shift = [- 4.5 * self.small_horisontal, -1.5 * self.small_vertical]

            # Shifted coordinate inside the chunk
            pre_point = [sum(k) for k in zip(chunk_start, start_shift)]
            # Shifted coordinate based on chunk shift from previous chunk
            point = [sum(n) for n in zip(pre_point, chunks_shift)]

            for line_number, line in enumerate(pattern):

                for item_position, item in enumerate(line):
                    # If there is something left in the list
                    if items_to_place:
                        # Take it out
                        popped = items_to_place.pop()
                        # And assign coordinates to the application
                        pattern[line_number][item_position] = popped
                        # And place the application into prepared template
                        point_coordinates[popped] = point
                    # If chunk order is odd and either this is the end of the row, or no more items to place
                    if self.chunk_is_odd(chunk_number + 1) and (item_position == 3 or not items_to_place):
                        line.reverse()
                    # If the end of the row is not reached yet, shift by app to app relation
                    if item_position != 3:
                        point = [sum(m) for m in zip(point, shift)]
                # Row end reached now, time to shift by app to row relation
                point = [sum(n) for n in zip(point, row_shift)]
            # Chunk ended now, time to shift chunk center by chunk to chunk relation
            chunk_start = [sum(o) for o in zip(chunk_start, chunks_shift)]
            # Save the structured chunk just in case
            self.chunks_structure[chunk_number] = pattern
        # Now store all the coordinates we have from application placing
        self.apps_coordinates = point_coordinates

    def pan_coordinates(self):
        """
        Figures out minimal coordinates (there are negative ones) and shifts all the coordinates by that difference
        This is needed for all the chunks to be visible when we draw the image
        """
        min_x = 0
        min_y = 0

        for key, coordinate in self.apps_coordinates.items():

            if coordinate[0] < min_x:
                min_x = coordinate[0]

            if coordinate[1] < min_y:
                min_y = coordinate[1]

        # Adding this to have spacing on the top and left of the image
        min_x -= self.large_horisontal
        min_y -= self.large_vertical

        # Shifting all the coordinates by minimals
        for key, coordinate in self.apps_coordinates.items():
            self.apps_coordinates[key] = [sum(z) for z in zip(coordinate, [- min_x, - min_y])]

    def get_canvas_dimensions(self):
        """
        Figures out final image dimensions
        """
        max_x = 0
        max_y = 0

        for key, value in self.apps_coordinates.items():

            if value[0] > max_x:
                max_x = value[0]

            if value[1] > max_y:
                max_y = value[1]
        # Adding this to have spacing on the bottom and right of the image
        max_x += self.large_horisontal
        max_y += self.large_vertical
        # Storing final dimensions for later use
        self.canvas_dimensions = [int(max_x), int(max_y)]

    def to_json(self):
        """
        Converts coordinates and canvas dimensions to json dump string
        """
        data = {'canvas_dimensions': self.canvas_dimensions,
                'application_coordinates': self.apps_coordinates}

        self.json_data = json.dumps(data)

    def output_json(self, filename):
        """
        Outputs json data to the file
        """
        with open(filename, 'w') as out_file:
            out_file.write(self.json_data)

    def output_image(self, filename):
        """
        Draws and outputs an image of chunks and applications
        """
        background_dimensions = (self.canvas_dimensions[0], self.canvas_dimensions[1])
        # Used tint of red to indicate transparency
        background = Image.new('RGBA', background_dimensions, (127, 0, 0, 0))
        # 'polygon' used to get transparency by pasting the chunk over background
        polygon_dimensions = (int(round(self.large_horisontal)), int(round(self.large_vertical)))
        # If on Windows, 'Windows/fonts/' folder is looked into
        font = ImageFont.truetype('verdana.ttf', 48)

        # Extract coordinates from apps_coordinates
        for key, value in self.apps_coordinates.items():
            # Coordinates are inside polygon, so polygon_dimensions is used
            point_north = (175, 0)
            point_east = (350, 87.5)
            point_south = (175, 175)
            point_west = (0, 87.5)
            # (0, 0) of each polygon
            polygon_offset = (int(round(value[0] - self.large_half_horisontal)),
                              int(round(value[1] - self.large_half_vertical)))
            polygon = Image.new('RGBA', polygon_dimensions)
            polydraw = ImageDraw.Draw(polygon)
            # Used tint of blue to indicate transparency, resulting polygon should be purple-ish
            polydraw.polygon([point_north, point_east, point_south, point_west],
                             fill=(0, 0, 127, 127),
                             outline=(0, 0, 127, 255))
            text_string = str(key)
            w, h = font.getsize(text_string)
            # Draw a text with chunk number over the polygon. The text is placed in the center of polygon
            # accounting for text dimensions
            polydraw.text(((350 - w) / 2, ((175 - h) / 2)), text_string, fill=(255, 255, 255), font=font)
            background.paste(polygon, polygon_offset, mask=polygon)

        background.save(filename, 'PNG')


def main():
    # Fair timing of total time used to execute the script starts here
    total_start_time = timeit.default_timer()

    class CapitalisedHelpFormatter(argparse.RawTextHelpFormatter):
        """
        Cosmetics. Used to override 'usage: ' string to 'Usage: '
        """

        def add_usage(self, usage, actions, groups, prefix=None):
            if prefix is None:
                prefix = 'Usage: '

            return super(CapitalisedHelpFormatter, self).add_usage(usage, actions, groups, prefix)

    def check_integer(value):
        """
        Input validation for amount of applications, which should always be positive integer
        """
        if not value.isdigit():
            raise argparse.ArgumentTypeError(f'{value} is not a invalid positive integer value')

        return int(value)

    # Command line stuff
    arg_parser = argparse.ArgumentParser(description='Maps integer amount of applications and outputs PNG image',
                                         formatter_class=CapitalisedHelpFormatter,
                                         add_help=False,
                                         prog="test_case_spacehug")

    # I know this is not good, but
    arg_parser._positionals.title = 'Positional arguments'
    arg_parser._optionals.title = 'Optional arguments'

    # Adding args
    arg_parser.add_argument('-h', '--help', action='help',
                            default=argparse.SUPPRESS,
                            help='Show this message and exit')

    arg_parser.add_argument('-v', '--version', action='version',
                            version=f'%(prog)s {__VERSION__}',
                            help='Show program version number and exit')

    arg_parser.add_argument('-a', '--apps',
                            dest='amount_of_applications',
                            required=True,
                            type=check_integer,
                            help='Process specified amount of applications, integers only')

    arg_parser.add_argument('-oj', '--output-json',
                            dest='json_file',
                            required=True,
                            help='Output processed applications to json matrix with given name')

    arg_parser.add_argument('-oi', '--output-image',
                            dest='image_file',
                            required=True,
                            help='Output processed applications to png image with given name')

    # Now, parse
    command_line = arg_parser.parse_args()
    amount_of_applications = command_line.amount_of_applications
    png_filename = command_line.image_file
    json_filename = command_line.json_file

    # Fair timer for json matrix generation starts here
    matrix_start_time = timeit.default_timer()

    # Init, innit?
    appmap = Map(amount_of_applications)

    # Do stuff now. Could be compacted or used in chains or anything else, but for the sake of visibility:
    appmap.get_array_size()
    appmap.locate_array_center()
    appmap.get_coordinates_delta()
    appmap.fill_chunks_map()
    appmap.place_applications()
    appmap.pan_coordinates()
    appmap.get_canvas_dimensions()
    appmap.to_json()

    # The json matrix is generated by now, the timer should be stopped gracefully
    matrix_end_time = timeit.default_timer()

    # Now saving the matrix to the file
    appmap.output_json(json_filename)
    logger.info(f'JSON matrix written to {json_filename}')

    # Now generate and save the image
    appmap.output_image(png_filename)
    logger.info(f'PNG image written to {png_filename}')

    # Calc matrix generation time and log it to console
    generation_time_sec = matrix_end_time - matrix_start_time
    generation_time_msec = round(generation_time_sec, 3)
    logger.info(f'Matrix generation took {generation_time_sec} seconds (~ {int(generation_time_msec * 1000)} msec)')

    # Calc total script execution time and log it to console too
    total_end_time = timeit.default_timer()
    total_time_sec = total_end_time - total_start_time
    total_time_msec = round(total_time_sec, 3)
    logger.info(f'Script execution took {total_time_sec} seconds (~ {int(total_time_msec * 1000)} msec)')

if __name__ == '__main__':
    main()
