import os
import time
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# 1. 从Excel文件读取经纬度数据
excel_file = 'GlobalCities.xlsx'

df = pd.read_excel(excel_file, sheet_name=0)  # 读取第一个sheet
latitude_column = 4  # 纬度在第5列（从0开始计数）
longitude_column = 5  # 经度在第6列
city_column = 1  # 城市名称在第2列
country_column = 2  # 国家名称在第3列

# 确保输出文件夹存在
output_folder = 'WeatherData'
os.makedirs(output_folder, exist_ok=True)

# NASA POWER API相关设置
api_url = "https://power.larc.nasa.gov/api/temporal/hourly/point"
parameters = "ALLSKY_SFC_SW_DNI,T2M"  # 要请求的参数

def sanitize_filename(name):
    # Convert name to string if it is not already
    name = str(name)
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name

# 读取已处理文件名中的城市名
def get_processed_cities():
    processed_cities = set()
    for file_name in os.listdir(output_folder):
        if file_name.endswith('.xlsx'):
            parts = file_name.split('_')
            if len(parts) > 3:
                city_name = parts[2]
                processed_cities.add(city_name)
    return processed_cities

# 定义请求数据的函数
def fetch_weather_data(latitude, longitude, city_name, country_name):
    latitude_formatted = f"{latitude:.3f}"
    longitude_formatted = f"{longitude:.3f}"
    # 当前请求的经纬度变量（后续可能被对调）
    cur_lat = latitude_formatted
    cur_lon = longitude_formatted
    swapped = False  # 标记是否已经对调过经纬度
    
    print(f"Processing data for latitude: {latitude_formatted}, longitude: {longitude_formatted}, city: {city_name}, country: {country_name}")

    years = [2021, 2022, 2023]
    all_data = []
    all_years_failed = True  # 用于标记该城市的所有年份是否都失败

    for year in years:
        start_date = f"{year}0101"  # YYYYMMDD格式起始日期
        end_date = f"{year}1231"    # YYYYMMDD格式结束日期
        
        retry_count = 0
        while retry_count < 3:

            params = {
                'start': start_date,
                'end': end_date,
                'latitude': cur_lat,
                'longitude': cur_lon,
                'community': 're',          # 指定社区
                'parameters': parameters,   # 请求参数：DNI和T2M
                'format': 'json',           # 返回JSON格式
                'user': 'YourAPIName',      # 替换成你的NASA API账户名
                'header': 'true',           # 返回头信息
                'time-standard': 'lst'      # 使用当地标准时间
            }

            response = requests.get(api_url, params=params, headers={'accept': 'application/json'})

            if response.status_code == 429:
                print(f"Received 429 for year {year} (attempt {retry_count + 1}). Waiting 10 seconds before retrying...")
                time.sleep(10)  # 等待10秒再重试
            # elif response.status_code == 422:
            #     print(f"Received 422 for year {year}. Skipping this year without retrying...")
            #     break  # 如果返回422，直接跳出当前循环，不再重试该年份
            elif response.status_code == 422:
                if not swapped:
                    print(f"Received 422 for year {year} with original coordinates. Swapping latitude and longitude and retrying for this year and subsequent requests...")
                    # 交换当前使用的经纬度
                    cur_lat, cur_lon = cur_lon, cur_lat
                    swapped = True
                    # 重置重试计数后重新尝试请求
                    retry_count = 0
                    continue
                else:
                    print(f"Received 422 even after swapping coordinates for year {year}. Skipping this year without retrying...")
                    break  # 已对调过但仍然返回422，跳出当前年份的请求循环
            elif response.status_code == 200:
                # 请求成功，处理数据
                data = response.json()

                # 提取当前年份的数据
                dni_data = data['properties']['parameter']['ALLSKY_SFC_SW_DNI']
                t2m_data = data['properties']['parameter']['T2M']
                timestamps = list(dni_data.keys())  # 获取所有时间戳（字符串形式）

                # 将时间戳（YYYYMMDDHH格式）转换为pandas datetime格式
                timestamps = pd.to_datetime(timestamps, format='%Y%m%d%H')

                # 构造DataFrame，包含时间戳、DNI和T2M
                weather_df = pd.DataFrame({
                    'Timestamp': timestamps,
                    'DNI': list(dni_data.values()),
                    'T2M': list(t2m_data.values())
                })

                # 将每年的数据添加到all_data列表中
                all_data.append(weather_df)
                all_years_failed = False  # 如果成功获取了数据，则标记为False
                break  # 成功获取数据，退出重试循环
            else:
                retry_count += 1
                if retry_count < 3:
                    print(f"Error fetching data for year {year} (attempt {retry_count}): {response.status_code}. Retrying in 2 seconds...")
                    time.sleep(2)  # 如果请求失败，等待2秒再尝试
                else:
                    print(f"Error fetching data for year {year} after {retry_count} attempts: {response.status_code} - {response.text}")
                    break  # 重试次数达到最大值，跳过该年的数据处理

    if all_years_failed:
        print(f"Skipping city {city_name}, all years failed.")
        return None  # 如果所有年份都失败，返回 None，跳过该城市

    # 合并三个年份的数据
    full_data = pd.concat(all_data, axis=0)

    # 计算每条记录在该年中的小时索引（0～8759），公式：(dayofyear - 1)*24 + hour
    full_data['HourIndex'] = (full_data['Timestamp'].dt.dayofyear - 1) * 24 + full_data['Timestamp'].dt.hour

    # 6. 按 HourIndex 分组求平均（聚合2021-2023同一小时的数据）
    hourly_avg = full_data.groupby('HourIndex')[['DNI', 'T2M']].mean().reset_index()

    # # 检查结果行数是否为8760
    # print(f"Total hours in averaged data: {len(hourly_avg)}")

    # 7. 定义输出Excel文件名（包含经纬度、城市和国家信息）
    sanitized_city = sanitize_filename(city_name)
    sanitized_country = sanitize_filename(country_name)
    file_name = f"{cur_lon}_{cur_lat}_{sanitized_city}_{sanitized_country}_DNI_T2M_Hourly_Avg_2021-2023.xlsx"
    file_path = os.path.join(output_folder, file_name)

    # file_name = f"{cur_lon}_{cur_lat}_{city_name}_{country_name}_DNI_T2M_Hourly_Avg_2021-2023.xlsx"
    # file_path = os.path.join(output_folder, file_name)

    # 保存最终分组结果到Excel文件，sheet名称为 "Hourly Average DNI and T2M"
    hourly_avg.to_excel(file_path, sheet_name="Hourly Average DNI and T2M", index=False)
    print(f"Data saved to {file_path}")

# 使用ThreadPoolExecutor并行处理多个城市的数据
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = []
    processed_cities = get_processed_cities()  # 获取已经处理过的城市名
    for index, row in df.iterrows():
        city_name = row.iloc[city_column]
        if city_name not in processed_cities:  # 如果该城市的数据已处理过，则跳过
            latitude = row.iloc[latitude_column]
            longitude = row.iloc[longitude_column]
            country_name = row.iloc[country_column]
            # 提交任务到线程池
            futures.append(executor.submit(fetch_weather_data, latitude, longitude, city_name, country_name))
        else:
            print(f"Skipping city {city_name}, data already processed.")

    # 等待所有任务完成
    for future in as_completed(futures):
        result = future.result()  # 获取结果，确保任务完成
        if result is None:
            print(f"City skipped due to data fetch failure.")