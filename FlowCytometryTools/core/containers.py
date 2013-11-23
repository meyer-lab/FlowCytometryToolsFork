'''
Created on Jun 14, 2013

@author: jonathanfriedman

TODO:
'''
from FlowCytometryTools import parse_fcs
from bases import Measurement, MeasurementCollection, OrderedCollection
from GoreUtilities.util import to_list
from itertools import cycle
import graph
import inspect
import numpy as np
from FlowCytometryTools.core.transforms import Transformation

class FCMeasurement(Measurement):
    '''
    A class for holding flow cytometry data from
    a single well or a single tube.
    '''

    @property
    def channels(self):
        '''
        Channel information organized as a DataFrame
        '''
        if self.meta is not None:
            return self.meta['_channels_']
        
    @property
    def channel_names(self):
        '''
        A tuple containing the channel names
        '''
        if self.meta is not None:
            return self.meta['_channel_names_']

    def read_data(self, **kwargs):
        '''
        Read the datafile specified in Sample.datafile and
        return the resulting object.
        Does NOT assign the data to self.data
        '''
        meta, data = parse_fcs(self.datafile, **kwargs)
        return data

    def read_meta(self, **kwargs):
        '''
        '''
        kwargs['meta_data_only'] = True
        kwargs['reformat_meta'] = True
        meta = parse_fcs(self.datafile, **kwargs)
        return meta
    
    def get_meta_fields(self, fields, kwargs={}):
        '''
        Return a dictionary of metadata fields
        '''
        fields = to_list(fields)
        meta = self.get_meta()
        return dict( ((field, meta.get(field)) for field in fields ) )

    def ID_from_data(self, ID_field='$SRC'):
        '''
        Returns the well ID from the src keyword in the FCS file. (e.g., A2)
        This keyword may not appear in FCS files generated by other machines,
        in which case this function will raise an exception.
        '''
        try:
            return self.get_meta_fields(ID_field)[0]
        except:
            raise Exception("The keyword '{}' does not exist in the following FCS file: {}".format(ID_field, self.datafile))

    def plot(self, channel_names, transform=(None, None), kind='histogram', 
             gates=None, transform_first=True, apply_gates=True, plot_gates=True,
             gate_colors=None, **kwargs):
        '''
        Plots the flow cytometry data associated with the sample on the current axis.
        Follow with a call to matplotlibs show() in order to see the plot.

        Parameters
        ----------
        channel_names : str| iterable of str | None
            name (names) channels to plot.
            given a single channel plots a histogram
            given two channels produces a 2d plot
        transform : valid transform | tuple of valid transforms | None
            Transform to be applied to corresponding channels using the FCMeasurement.transform function.
            If a single transform is given, it will be applied to all plotted channels.
        kind : 'scatter', 'histogram'
        gates: Gate| iterable of Gate | None
            Gates to be applied before plotting
        transform_first : bool
            Apply transforms before gating.
        kwargs : dict
            Additional keyword arguments to be passed to graph.plotFCM

        Returns
        -------
        None: if no data is loaded
        gHandle: reference to axis
        '''
#         data = self.get_data() # The index is to keep only the data part (removing the meta data)
        # Transform sample

        def _trans(sample, channel_names, transformList):
            for c,t in zip(channel_names, transformList):
                if t is not None:
                    sample = sample.transform(t, channels=c)
                else:
                    pass
            return sample
        
        def _gates(sample, gates):
            if gates is None:
                return sample
            for gate in gates:
                sample = sample.gate(gate)
            return sample
        
        ax = kwargs.get('ax')
        
        channel_names = to_list(channel_names)
        transformList = to_list(transform)
        gates         = to_list(gates)
        
        if len(transformList) == 1:
             transformList *= len(channel_names)
        
        sample_tmp = self.copy()
        if apply_gates:
            if transform_first:
                sample_tmp = _trans(sample_tmp, channel_names, transformList)
                sample_tmp = _gates(sample_tmp, gates)
            else:
                sample_tmp = _gates(sample_tmp, gates)
                sample_tmp = _trans(sample_tmp, channel_names, transformList)
        else:
            sample_tmp = _trans(sample_tmp, channel_names, transformList)
            
        data = sample_tmp.get_data()
        out  = graph.plotFCM(data, channel_names, kind=kind, **kwargs)
        
        if plot_gates and gates is not None:
            if gate_colors is None:
                gate_colors = cycle(('b', 'g', 'r', 'm', 'c', 'y'))
            for (g,c) in zip(gates, gate_colors):
                g.plot(ax=ax, ax_channels=channel_names, color=c)
        
        return out

    def view(self):
        '''
        Loads the current FCS sample viewer

        Parameters
        ----------
        channel_names : str | list of str
            (Not implemented yet)
            Names of channels to load by default

        Returns
        -------

        TODO: Implement channel_names
        '''
        #if launch_new_subprocess: # This is not finished until I can list the gates somewhere
            #from FlowCytometryTools import __path__ as p
            #from subprocess import call
            #import os
            #script_path = os.path.join(p[0], 'GUI', 'flomeasurementwGUI.py')
            #call(["python", script_path, self.datafile])
        #else:
        from FlowCytometryTools.GUI import gui
        return gui.launch_from_fc_measurement(self)

    def transform(self, transform, direction='forward',  
                  channels=None, return_all=True, auto_range=True,
                  use_spln=True, get_transformer=False, ID = None, 
                  args=(), **kwargs):
        '''
        Apply transform to specified channels. 
        The transformation parameters are shared between all transformed channels.
        If different parameters need to be applied to different channels, use several calls to `transform`.
        
        Parameters
        ----------
        transform : callable | str
            Callable that does a transformation (should accept a number or array),
            or one of the supported named transformations.
            Supported transformation are: {}. 
        direction : 'forward' | 'inverse'
            Direction of transformation.
        channels : str | list of str | None
            Names of channels to transform.
            If None is given, all channels will be transformed.
            .. warning:: Time channels will also be transformed if all channels are transformed.
        return_all : bool
            True -  return all columns, with specified ones transformed.
            False - return only specified columns.
        auto_range : bool 
            If True data range (machine range) is automatically extracted from $PnR field of metadata.
            .. warning:: If the data has been previously transformed its range may not match the $PnR value.
                In these cases auto_range should be set to False.
        use_spln : bool
            If True th transform is done using a spline. 
            See Transformation.transform for more details.
        get_transformer : bool
            If True the transformer is returned in addition to the new Measurement. 
        ID : hashable | None
            ID for the resulting collection. If None is passed, the original ID is used.
        args : 
            Additional positional arguments to be passed to the Transformation.
        kwargs :
            Additional keyword arguments to be passed to the Transformation.
            
        Returns
        -------
        new : FCMeasurement
            New measurement containing the transformed data.
        transformer : Transformation
            The Transformation applied to the input measurement.
            Only returned if get_transformer=True.
        
        Examples
        --------
        >>> trans = original.transform('hlog')
        >>> trans = original.transform('tlog', th=2)
        >>> trans = original.transform('hlog', d=log10(2**18), auto_range=False)
        >>> trans = original.transform('hlog', r=1000, use_spln=True, get_transformer=True)
        >>> trans = original.transform('hlog', channels=['FSC-A', 'SSC-A'], b=500).transform('hlog', channels='B1-A', b=100)
        '''
        data = self.get_data()

        channels = to_list(channels)
        if channels is None:
            channels = data.columns
        ## create transformer
        if isinstance(transform, Transformation):
            transformer = transform
        else: 
            if auto_range: #determine transformation range
                if 'd' in kwargs:
                    warnings.warn('Encountered both auto_range=True and user-specified range value in parameter d.\n Range value specified in parameter d is used.') 
                else:
                    channel_meta = self.get_meta()['_channels_']
                    ranges = []
                    for i,r in channel_meta.iterrows():
                        if r['$PnN'] in channels: ranges.append(float(r['$PnR']))
                    if not np.allclose(ranges, ranges[0]):
                        raise Exception, 'Not all specified channels have the same data range, therefore they cannot be transformed together.'
                    kwargs['d'] = np.log10(ranges[0])
            transformer = Transformation(transform, direction, args, **kwargs)        
        ## create new data
        transformed = transformer(data[channels], use_spln)   
        if return_all:
            new_data = data
        else:
            new_data = data.filter(columns)
        new_data[channels] = transformed
        ## create new Measurement
        new = self.copy()    
        new.set_data(data=new_data)
        
        if ID is not None:
            new.ID = ID
        if get_transformer:
            return new, transformer
        else:
            return new       

    def gate(self, gate):
        '''
        Apply given gate and return new gated sample (with assigned data).
        Note that no transformation is done by this funciton.
        '''
        data = self.get_data()
        newdata = gate(data)
        newsample = self.copy()
        newsample.set_data(data=newdata)
        return newsample
    
    @property
    def counts(self):
        data = self.get_data()
        return data.shape[0]       

class FCCollection(MeasurementCollection):
    '''
    A dict-like class for holding flow cytometry samples.
    '''
    _measurement_class = FCMeasurement
    
    def transform(self, transform, direction='forward', share_transform=True, 
                  channels=None, return_all=True, auto_range=True,
                  use_spln=True, get_transformer=False, ID = None, 
                  args=(), **kwargs):
        '''
        Apply transform to each Measurement in the Collection. 
        Return a new Collection with transformed data.
        .. warning : The new Collection will hold the data for **ALL** Measurements in memory!
        
        Parameters
        ----------
        transform : callable | str
            Callable that does a transformation (should accept a number or array),
            or one of the supported named transformations.
            Supported transformation are: {}. 
        share_transform : bool
            True - same transformer will be used for all measurements in the collection.
            False - a new transformer will be created for each measurement, allowing for varying data ranges. 
        direction : 'forward' | 'inverse'
            Direction of transformation.
        channels : str | list of str | None
            Names of channels to transform.
            If None is given, all channels will be transformed.
            .. warning:: Time channels will also be transformed if all channels are transformed.
        return_all : bool
            True -  return all columns, with specified ones transformed.
            False - return only specified columns.
        auto_range : bool 
            If True data range (machine range) is automatically extracted from $PnR field of metadata.
            .. warning:: If the data has been previously transformed its range may not match the $PnR value.
                In these cases auto_range should be set to False.
        use_spln : bool
            If True th transform is done using a spline. 
            See Transformation.transform for more details.
        get_transformer : bool
            If True the transformer is returned in addition to the new Measurement.
        ID : hashable | None
            ID for the resulting collection. If None is passed, the original ID is used.
        args : 
            Additional positional arguments to be passed to the Transformation.
        kwargs :
            Additional keyword arguments to be passed to the Transformation.
            
        Returns
        -------
        new : FCCollection
            New collection containing the transformed measurements.
        transformer : Transformation
            The Transformation applied to the measurements.
            Only returned if get_transformer=True & share_transform=True.
        
        Examples
        --------
        >>> trans = original.transform('hlog')share_transform
        >>> trans = original.transform('tlog', th=2)
        >>> trans = original.transform('hlog', d=log10(2**18), auto_range=False)
        >>> trans = original.transform('hlog', r=1000, use_spln=True, get_transformer=True)
        >>> trans = original.transform('hlog', channels=['FSC-A', 'SSC-A'], b=500).transform('hlog', channels='B1-A', b=100)
        '''
        new = self.copy()
        if share_transform:
            meta = self.values()[0].get_meta()
            channels = to_list(channels)
            if channels is None:
                channels = meta['_channels_']['$PnN'].values
            ## create transformer
            if isinstance(transform, Transformation):
                transformer = transform
            else: 
                if auto_range: #determine transformation range
                    if 'd' in kwargs:
                        warnings.warn('Encountered both auto_range=True and user-specified range value in parameter d.\n Range value specified in parameter d is used.') 
                    else:
                        channel_meta = meta['_channels_']
                        ranges = []
                        for i,r in channel_meta.iterrows():
                            if r['$PnN'] in channels: ranges.append(float(r['$PnR']))
                        if not np.allclose(ranges, ranges[0]):
                            raise Exception, 'Not all specified channels have the same data range, therefore they cannot be transformed together.'
                        kwargs['d'] = np.log10(ranges[0])
                transformer = Transformation(transform, direction, args, **kwargs)
                if use_spln:
                    xmax = 10**kwargs['d']
                    transformer.set_spline(-xmax, xmax)
            ## transform all measurements     
            for k,v in new.iteritems(): 
                new[k] = v.transform(transformer, channels=channels, return_all=return_all, use_spln=use_spln)
        else:
            for k,v in new.iteritems(): 
                new[k] = v.transform(transform, direction=direction, channels=channels, 
                                     return_all=return_all, auto_range=auto_range, get_transformer=False,
                                     use_spln=use_spln, args=args, **kwargs)
        if ID is not None:
            new.ID = ID
        if share_transform and get_transformer:
            return new, transformer
        else:
            return new

    def gate(self, gate, ID=None):
        '''
        Apply gate to each Measurement in the Collection. 
        Return a new Collection with gated data.
        Note that the new Collection will hold the data for ALL Measurements in memory!
        
        see FCMeasurement.gate for more details.
        '''
        new = self.copy()
        for k,v in new.iteritems(): 
            new[k] = v.gate(gate)
        if ID is not None:
            new.ID = ID
        return new
    
    def counts(self, ids=None, setdata=False, output_format='DataFrame'):
        '''
        Return the counts in each of the specified measurements.
        
        Parameters
        ----------
        ids : hashable| iterable of hashables | None
            Keys of measurements to get counts of.
            If None is given get counts of all measurements. 
        setdata : bool
            Whether to set the data in the Measurement object.
            Used only if data is not already set.
        output_format: 'DataFrame' | 'dict
                
        Returns
        -------
        DataFrame/Dictionary keyed by measurement keys containing the corresponding counts.
        ''' 
        return self.apply(lambda x:x.counts, ids=ids, setdata=setdata, output_format=output_format)   


class FCOrderedCollection(OrderedCollection, FCCollection):
    '''
    A dict-like class for holding flow cytometry samples that are arranged in a matrix.
    '''
    def plot(self, channel_names,  kind='histogram', transform=(None, None),
             gates=None, transform_first=True, apply_gates=True, plot_gates=True, gate_colors=None,
             ids=None, row_labels=None, col_labels=None,
             xlim=None, ylim=None,
             autolabel=True,
             **kwargs):
        """
        For details see documentation for FCMeasurement.plot
        **kwargs passes arguments to both grid_plot and to FCMeasurement.plot.

        Note
        -------
        The function assumes that grid_plot and FCMeasurement.plot use unique key words.
        Any key word arguments that appear in both functions are passed only to grid_plot in the end.

        Returns
        -------
        gHandleList: list
            gHandleList[0] -> reference to main axis
            gHandleList[1] -> a list of lists
                example: gHandleList[1][0][2] returns the subplot in row 0 and column 2

        Examples
        ------------
        Below, plate is an instance of the FCOrderedCollection

        plate.plot(['SSC-A', 'FSC-A'], kind='histogram', transform='hlog', autolabel=True)

        plate.plot(['SSC-A', 'FSC-A'], transform='hlog', xlim=(0, 10000))

        plate.plot(['B1-A', 'Y2-A'], transform='hlog', kind='scatter', color='red', s=1, alpha=0.3)
        """
        ###
        # Automatically figure out which of the kwargs should
        # be sent to grid_plot instead of two sample.plot
        # (May not be a robust solution, we'll see as the code evolves
        grid_arg_list = inspect.getargspec(OrderedCollection.grid_plot).args

        grid_plot_kwargs = { 'ids' :  ids,
                             'row_labels' :  row_labels,
                             'col_labels' :  col_labels}

        for key, value in kwargs.items():
            if key in grid_arg_list:
                kwargs.pop(key)
                grid_plot_kwargs[key] = value

        ##########
        # Defining the plotting function that will be used.
        # At the moment grid_plot handles the labeling 
        # (rather than sample.plot or the base function
        # in GoreUtilities.graph

        def plot_sample(sample, ax):
            return sample.plot(channel_names, transform=transform, ax=ax,
                               gates=gates, transform_first=transform_first, apply_gates=apply_gates, 
                               plot_gates=plot_gates, gate_colors=gate_colors,
                               colorbar=False,
                               kind=kind, autolabel=False, **kwargs)

        xlabel, ylabel = None, None

        if autolabel:
            cnames = to_list(channel_names)
            xlabel=cnames[0]

            if len(cnames) == 2:
                ylabel=cnames[1]

        return self.grid_plot(plot_sample, xlim=xlim, ylim=ylim,
                    xlabel=xlabel, ylabel=ylabel,
                    **grid_plot_kwargs)
            

FCPlate = FCOrderedCollection

if __name__ == '__main__':
    import glob
    datadir = '../tests/data/Plate01/'
    fname = glob.glob(datadir + '*.fcs')[0]
    sample = FCMeasurement(1, datafile=fname)
    #print sample.channels
    #print sample.channel_names
#     hs = sample.transform('hlog', use_spln=True)
#     hs.plot(('FSC-A','SSC-A'))
#     import pylab
#     pylab.show()

    plate = FCPlate.from_dir('p', datadir).dropna()
    print plate.counts()
    print plate

    import time
    s = time.clock()
    hplate = plate.transform('hlog', channels=['FSC-A', 'SSC-A'], use_spln=False)
    e = time.clock()
    
    ss = time.clock()
    hplate = plate.transform('hlog', channels=['FSC-A', 'SSC-A'])
    es = time.clock()
    print e-s, es-ss
    #print plate.wells 
    #print plate.well_IDS
    
    #plate.apply(lambda x:x.ID, 'ID', applyto='sample', well_ids=['A1','B1'])
    #plate.apply(lambda x:x.datafile, 'file', applyto='sample')
    #plate.apply(lambda x:x.shape[0], 'counts', keepdata=True)
    #plate.get_well_metadata(['date', 'etim'])
    #print plate.extracted['file'].values
    
#     plate.wells['1']['A'].get_metadata()
#     
#     well_ids = ['A2' , 'B3']
#     print plate.get_wells(well_ids)
#     
#     plate.clear_well_data()  
#     plate.clear_well_data(well_ids)             
            
        