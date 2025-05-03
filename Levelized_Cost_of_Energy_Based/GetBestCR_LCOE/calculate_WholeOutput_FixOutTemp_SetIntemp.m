function LCOEBased = calculate_WholeOutput_FixOutTemp_SetIntemp(CR, SolarIR, FixOutTemp)
    % 1. 构造掩码，只保留 SolarIR >= 50 的行
    SolarIR = SolarIR .* CR;
    mask = SolarIR >= 50;
    
    % 2. 过滤辐照度和环境温度
    IRR = SolarIR(mask);     % 剔除 <50 的辐照度
    AT  = 15;     % 对应行的环境温度
    
    % 3. 变动流量标量：批量求解每一行所需的 V
    %    传入向量 IRR、AT 和标量 CR、FixOutTemp
    V = solve_for_V(IRR, AT, FixOutTemp);

    % 4. 剔除 V < 0.1 的行
    mask2 = V >= 0.1;
    IRR = IRR(mask2);    % 同步剔除对应行
    V   = V(mask2);

    % 5. 向量化计算每一行的效率贡献 outPower
    outPower = 18.36607 + 0.046317 .* IRR - 0.766644 .* AT + 0.009821 .* V ...
               - 0.000150 .* IRR .* AT + 0.000040 .* IRR .* V + 0.000163 .* AT .* V ...
               - 1.12660E-6 .* IRR.^2 + 0.017270 .* AT.^2 - 0.000089 .* V.^2;

    outThermal = (V ./ 3600) * 4180 .* (FixOutTemp - AT);

    % 6. 最后求和
    outputPower = sum(outPower)/0.38 + sum(outThermal);

    % 7. 费用
    InitCost = 68.94 * 0.2 * 1 + 15 * 0.2 * 1 * CR + CR * (50 + 15 + 20 + 100) + 550;

    CRRelatedOM = 0 / 100;

    LandLeaseCost = 20 / 100;

    cost = InitCost + (InitCost * (0.04 + (CR - 1) * CRRelatedOM) + LandLeaseCost) * 8.8633;

    % 8. LCOE
    LCOEBased = cost / outputPower / 8.8633;

end

function V_vals = solve_for_V(IRR, AT, FixOutTemp)

    % 方程分行表示
    term1 = -3.37466 + 0.00844 .* IRR + 1.01901 .* AT + 3.31214e-06 .* IRR .* AT;
    denom = -0.001456 - 0.000017 .* IRR + 0.000077 .* AT;
    
    % 求解V的表达式
    V_vals = (FixOutTemp - term1) ./ denom;

    % V_vals_test = term1 + V_vals.* denom;

end