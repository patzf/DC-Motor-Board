import numpy as np


class RingBuffer:

    def __init__(self, size):

        self.size = size

        self.buffer = np.zeros(
            size,
            dtype=np.float64
        )

        self.index = 0

        self.full = False


    def append(self, value):

        self.buffer[
            self.index
        ] = value

        self.index += 1

        if self.index >= self.size:

            self.index = 0

            self.full = True


    def get(self):

        if not self.full:

            return self.buffer[
                :self.index
            ]


        return np.roll(
            self.buffer,
            -self.index
        )


    def get_last(self, count):

        if count <= 0:

            return np.array([])


        available = len(self)


        if count > available:

            count = available


        if not self.full:

            return self.buffer[
                self.index-count:self.index
            ]


        start = (
            self.index -
            count
        )

        if start >= 0:

            return self.buffer[
                start:self.index
            ]


        return np.concatenate(
            (
                self.buffer[start:],
                self.buffer[:self.index]
            )
        )


    def clear(self):

        self.buffer.fill(
            0
        )

        self.index = 0

        self.full = False


    def __len__(self):

        if self.full:

            return self.size

        return self.index
