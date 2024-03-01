import copy

from science.analyze.object_collection import ObjectCollection
from ref.ref import target_file_default
from autostar.import_stars import CheckStarNames


class OutputObjectCollection(ObjectCollection):
    """
    A mutable version of ObjectCollection use for looking at specific targets or other subsets
    of ObjectCollection data.

    Note this integrate all the methods of Object collection.
    """
    def receive_data(self, object_collection):
        """
        This is a hack to let a user convert an ObjectCollection data set to an
        OutputObjectCollection instance.
        :param object_collection: an instance to save and avoid reloading the data.
        :return:
        """
        self.__dict__.update(copy.deepcopy(object_collection.__dict__))

    def flag_targets(self, target_spexodisks_handles):
        """
        For the given spexodisks_handles, turn those SingleObject.is_target to True

        :param target_spexodisks_handles:
        :return:
        """
        self.targets_requested = set(target_spexodisks_handles)
        self.targets_found = set()
        self.targets_not_found = set()
        self.targets_found_at_least_one_spectrum = set()
        self.targets_found_no_spectra = set()
        # See what target objects are in this instance of OutputObjectCollection
        for spexodisks_handle in list(self.targets_requested):
            if spexodisks_handle in self.available_spexodisks_handles:
                self.targets_found.add(spexodisks_handle)
                this_star = self.__getattribute__(spexodisks_handle)
                this_star.is_target = True
                if this_star.available_spectral_handles:
                    self.targets_found_at_least_one_spectrum.add(spexodisks_handle)
                else:
                    self.targets_found_no_spectra.add(spexodisks_handle)

            else:
                self.targets_not_found.add(spexodisks_handle)
        if self.verbose:
            print(F'Target Data Acquired for {self.target_file}.')
            requested_pop = sorted(self.pop_names_lib.handle_to_pop_name[handle] for handle in self.targets_requested)
            print(F'    Targets requested: {"%3i" % len(self.targets_requested)} : {requested_pop}')
            found_pop = sorted(self.pop_names_lib.handle_to_pop_name[handle] for handle in self.targets_found)
            print(F'        Targets found: {"%3i" % len(self.targets_found)} : {found_pop}')
            not_found_pop = sorted(self.pop_names_lib.handle_to_pop_name[handle] for handle in self.targets_not_found)
            print(F'    Targets not found: {"%3i" % len(self.targets_not_found)} : {not_found_pop}')
            found_with_spectra_pop = sorted(self.pop_names_lib.handle_to_pop_name[handle] for handle in
                                            self.targets_found_at_least_one_spectrum)
            print(F' Targets with spectra: {"%3i" % len(self.targets_found_at_least_one_spectrum)} : ' +
                  f'{found_with_spectra_pop}')
            found_without_spectra_pop = sorted(self.pop_names_lib.handle_to_pop_name[handle] for handle in
                                               self.targets_found_no_spectra)
            print(F'   Targets no spectra: {"%3i" % len(self.targets_found_no_spectra)} : ' +
                  f'{found_without_spectra_pop}\n')

    def read_target_list(self, target_file=None):
        """
        Read in a list of target star names. If those star names are in this instance of
        OutputObjectCollection turn that found SingleObject.is_target to True.

        :param target_file:
        :return: a list of star target  stars that were not in this instance of
        OutputObjectCollection
        """
        if target_file is None:
            target_file = target_file_default
        self.target_file = target_file
        if self.verbose:
            print('Getting data for targets...')
        if isinstance(self.target_file, str):
            # this is the case that the target file must be read-in and have its star names
            # converted to a list.
            if self.verbose:
                print(F'    Reading target star names in the file:{target_file}')
            csn = CheckStarNames(file_name=self.target_file)
            csn.update_simbad_ref()
            spexodisks_handles = csn.list_of_hypatia_handles
        else:
            csn = CheckStarNames(string_name_list=list(self.target_file))
            csn.update_simbad_ref()
            spexodisks_handles = csn.list_of_hypatia_handles
        if self.verbose:
            print('  SpExoDisks handles acquired for target stars.')
        self.flag_targets(target_spexodisks_handles=spexodisks_handles)

    def remove_non_targets(self):
        """
        Trim this class to get rid of the non target stars.
        :return:
        """
        stars_removed = 0
        if self.verbose:
            print("Removing not target star.")
        for spexodisks_handle in sorted(self.available_spexodisks_handles):
            single_object = self.__getattribute__(spexodisks_handle)
            if not single_object.is_target:
                stars_removed += 1
                self.__delattr__(spexodisks_handle)
                self.available_spexodisks_handles.remove(spexodisks_handle)
        if self.verbose:
            print("  Stars removed:", stars_removed)
            if self.available_spexodisks_handles == set():
                print("    remove_non_targets is returning an empty set of data.")

