function result = CalcuOpCR_FixOutTemp(SolarIR, envTemp, FixOutTemp)

    X_Dim = 1;

    %% 优化
    zhongqun = 50;
    cishu = 5000;
    
    f1 = @(CR)0.0 - calculate_WholeOutput_FixOutTemp_EnvIntemp(CR, SolarIR, envTemp, FixOutTemp) / (1 + CR * CR);   % 环境入口温度
    % f1 = @(CR)0.0 - calculate_WholeOutput_FixOutTemp_SetIntemp(CR, SolarIR, FixOutTemp) / (1 + CR * CR);   % 设定入口温度
    
    [data, obj] = platemo('algorithm',@SHADE,'objFcn',f1,'N',zhongqun,'maxFE',cishu,'D',X_Dim,'lower',1,'upper',20,'save',0);

    % 找到 obj 中最小值的索引
    [~, min_idx] = min(obj);

    result = data(min_idx);
    
    % disp(result);

end