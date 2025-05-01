function outputPower = calculate_WholeOutput_MaxTotalOutput(CR, SolarIR, envTemp)
    % 1. 构造掩码，只保留 SolarIR >= 50 的行
    SolarIR = SolarIR .* CR;
    mask = SolarIR >= 50;
    
    % 2. 过滤辐照度和环境温度
    IRR = SolarIR(mask);     % 剔除 <50 的辐照度
    AT  = envTemp(mask);     % 对应行的环境温度

    % 1. 构造掩码，只保留 AT >= 0 的行
    mask1 = AT >= 0;

    % 2. 过滤辐照度和环境温度
    IRR = IRR(mask1);
    AT  = AT(mask1);
    
    % 3. 固定流量标量
    V = 500;

    % 4. 向量化计算每一行的效率贡献 outPower
    outPower = 34.19766 + 0.118955 .* IRR - 1.87448 .* AT + 0.006302 .* V ...
               - 0.000095 .* IRR .* AT + 0.000037 .* IRR .* V + 0.000156 .* AT .* V ...
               - 1.08430e-6 .* IRR.^2 + 0.045354 .* AT.^2 - 0.000053 .* V.^2;

    % 6. 最后求和
    outputPower = sum(outPower);

end