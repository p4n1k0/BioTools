#!/opt/schrodinger/suites2018-4/run

from schrodinger.application.desmond.packages import topo, traj, traj_util, analysis
from schrodinger.structure import StructureWriter
from scipy.spatial.distance import squareform
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
import numpy as np
from scipy.spatial.distance import pdist
import matplotlib.pyplot as plt
import argparse
import sys

def main():
    args = argparse.ArgumentParser(description="Perform RMSD-based clustering of a Desmond MD")
    args.add_argument('cms', help="Cms input file")
    args.add_argument('out', help="Output base name")
    args.add_argument('-rmsd', help="Define ASL for RMSD calculation", required=True)
    args.add_argument('-fit', help="Define ASL for fitting;", default=False)
    args.add_argument('-n', help="Max number N of clusters", required=True)
    args.add_argument('-s', help="Split trajectory in sub trajectories containing frames of each cluster", action="store_true")
    args.add_argument('-tree', help="View cluster dendrogram and exit", action="store_true")
    args.add_argument('-save', help="Store intermediate distance matrix to FILE", default=False)
    args.add_argument('-restore', help="Load intermediate distance matrix from FILE", default=False)
    args = args.parse_args()

    # read trajectory
    msys, cms, trj = traj_util.read_cms_and_traj(args.cms)

    # specify atoms to consider form rmsd calc and fitting
    rmsd_aids = cms.select_atom(args.rmsd)
    rmsd_gids = topo.aids2gids(cms, rmsd_aids, include_pseudoatoms=False)

    # calc. distance matrix
    if args.restore:
        rmsd_matrix = np.fromfile(args.restore)
        rmsd_matrix.reshape(int(np.sqrt(len(rmsd_matrix))), int(np.sqrt(len(rmsd_matrix))))

    else:
        fit_aids = cms.select_atom(args.fit)
        fit_gids = topo.aids2gids(cms, fit_aids, include_pseudoatoms=False)
        rmsd_matrix = analysis.rmsd_matrix(msys, trj, rmsd_gids, fit_gids)

    if args.save:
        rmsd_matrix.tofile(args.save)

    # Clustering with scipy
    y = squareform(rmsd_matrix)
    Z = linkage(y, method='complete')
    labels = fcluster(Z, args.n, 'maxclust')
    
    if args.tree:
        dendrogram(Z)
        plt.show()
        return

    clusters = []
    centroids = []
    for i in range(1, args.n + 1):
        # Get the frame indexes from cluster labels
        elements = np.where(labels == i)[0]

        # Avoid storing empty lists
        if len(elements) > 0:
            clusters.append(elements)
            # Get the centroids by individuating the element with the minimum distance to
            # every other element of the same cluster
            c = np.argmin(np.sum(rmsd_matrix[elements, :][:, elements], axis=1))
            centroids.append(elements[c])

    trj = np.array(trj)
    for i,elements in enumerate(clusters, 1):
        traj.write_traj(trj[elements], f"{args.out}_{i}_trj")
	
    system_st = cms.extract(cms.atom)

    for i,centroid in enumerate(centroids, 1):
        st = system_st.copy()
        st.setXYZ(trj[centroid].pos())
        st.write(f"{args.out}_{i}-out.mae")
        

if __name__ == "__main__":
    main()
