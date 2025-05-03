clear;
clc;

% ———————— 配置 ————————
folderPath = 'E:\OptCR\WeatherData';
fileList   = dir(fullfile(folderPath, '*.xlsx'));
nFiles     = length(fileList);

% ———————— 启动并行池（80 个 workers） ————————
desiredWorkers = 80;
pool = gcp('nocreate');
if isempty(pool)
    parpool('local', desiredWorkers);
elseif pool.NumWorkers ~= desiredWorkers
    delete(pool);
    parpool('local', desiredWorkers);
end

% ———————— 从文件名提取经度、纬度、城市名 ————————
longitudes = zeros(nFiles,1);
latitudes  = zeros(nFiles,1);
cities     = cell(nFiles,1);
for i = 1:nFiles
    [~, baseName, ~] = fileparts(fileList(i).name);
    parts = strsplit(baseName, '_');
    % parts = {'0.150','40.100','Orpesa',…}
    longitudes(i) = str2double(parts{1});
    latitudes(i)  = str2double(parts{2});
    cities{i}     = parts{3};
end

% ———————— 调用 CalcuOpCR 并收集标量结果 ————————
results = nan(nFiles,1);
parfor i = 1:nFiles
    % 构造完整路径
    filePath = fullfile(fileList(i).folder, fileList(i).name);
    
    % 读取数据
    T       = readtable(filePath);
    SolarIR = T{:,2};      % 辐照强度
    envTemp = T{:,3};      % 环境温度

    FixOutTemp = 40;      % 固定输出温度设置
    
    % 处理并删除已完成的文件
    try
        % results(i) = CalcuOpCR_MaxTotalOutput(SolarIR, envTemp);   % 最大化地均总输出功
        results(i) = CalcuOpCR_FixOutTemp(SolarIR, envTemp, FixOutTemp);   % 固定输出温度最大化地均总输出功
        delete(filePath);   % 处理完就删除原文件
    catch ME
        warning('处理 %s 时出错：%s', fileList(i).name, ME.message);
    end
    
    fprintf('已处理并删除：%s --> Result = %g\n', fileList(i).name, results(i));
end

% ———————— 组成表格并写 Excel ————————
Toutput = table(longitudes, latitudes, cities, results, ...
    'VariableNames', {'Longitude','Latitude','City','Result'});

outputFile = 'CalcuOpCR_Results.xlsx';
writetable(Toutput, outputFile);
fprintf('所有文件的经度、纬度、城市和函数结果已保存到：%s\n', outputFile);