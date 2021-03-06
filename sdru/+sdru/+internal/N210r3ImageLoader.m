classdef N210r3ImageLoader < sdru.internal.N210ImageLoader
%N210r3ImageLoader SDRu image loader utility for N210 revision 3 radios

%   Copyright 2013 The MathWorks, Inc.

properties (Constant)
  Device = 'n210_r3';
end

properties (Constant, Access=protected)
  DefaultFPGAImage = ...
  	fullfile(sdru.internal.ImageLoaderBase.getDefaultImagePath(), ...
    'usrp_n210_r3_fpga.bin');
end

properties (Access = protected)
  UserSpecifiedFPGAImage
end
end