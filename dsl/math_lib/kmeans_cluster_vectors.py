
import numpy as np
from sklearn import cluster


class KMeansClusterVectors:
    def __init__(
        self,
        n_clusters=2,  # number of clusters for KMeans
        input_field="vector",  # field in the input dict containing points
        # field in the output dict to store cluster labels
        output_field_inc="cluster_incremental",
        # field in the output dict to store all cluster labels
        output_field_all="cluster_all",
        name="KMeansClusterVectors"  # default: name of this class
    ):
        self.n_clusters = n_clusters
        self.input_field = input_field
        self.output_field_inc = output_field_inc
        self.output_field_all = output_field_all
        self.name = name
        self.vectors_so_far = []
        self.labels = []
        self.kmeans = cluster.KMeans(n_clusters=2)

    def __call__(self, msg):
        v = msg[self.input_field]              # shape (1,2)
        self.vectors_so_far.append(v)
        print(f"self.vectors_so_far = {self.vectors_so_far}")
        X = np.vstack(self.vectors_so_far)
        if X.shape[0] < self.kmeans.n_clusters:
            msg[self.output_field_inc] = None
            msg[self.output_field_all] = None
            return msg
        self.labels = self.kmeans.fit_predict(X)
        print(f"labels = {self.labels}")
        msg[self.output_field_inc] = int(self.labels[-1])
        msg[self.output_field_all] = self.labels.tolist()

        return msg

    run = __call__
