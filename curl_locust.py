# ================= 自动安装依赖 =================
import sys
import subprocess
import os

def ensure(pkg):
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

ensure("flask")
ensure("locust")
ensure("faker")

# ================= imports =================
import re
import json
from urllib.parse import urlparse, parse_qs, urlunparse
from flask import Flask, request, render_template_string, jsonify, send_file
from io import BytesIO
import shlex

app = Flask(__name__)
app.generated_code = ""

# ================= Faker标记类 =================
class FakerExpr(str):
    """Faker表达式标记类，用于区分普通字符串和Faker代码表达式"""
    pass

# ================= HTML =================
HTML = """
<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>Clocust</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>
<link rel="shortcut icon" href="https://alvin.serv00.net/favicon_128.ico" type="image/x-icon">
<style>
body {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea, #764ba2);
}
.container { max-width: 1400px; }
.page-title { text-align:center; color:#fff; font-weight:700; }
.card {
  border-radius:16px;
  border:none;
  box-shadow:0 12px 30px rgba(0,0,0,.15);
}
textarea { font-family: "JetBrains Mono", monospace; font-size: 13px; }
#result { background:#0d1117; color:#c9d1d9; }
.step-config { opacity:.5; pointer-events:none; }
.step-config.enabled { opacity:1; pointer-events:auto; }
#loadChart { background:#fff; border-radius:12px; pointer-events:none; }
.param-row { border-bottom: 1px solid #eee; padding: 8px 0; }
.param-row:last-child { border-bottom: none; }
#paramTable { max-height: 400px; overflow-y: auto; }
.param-enabled { background-color: #fff3cd !important; }
.interface-filter { margin-bottom: 10px; }
.interface-filter select { max-width: 300px; }
.debug-btn { margin-left: 10px; }
.code-preview { 
  background: #f8f9fa; 
  padding: 10px; 
  border-radius: 5px; 
  font-family: monospace; 
  font-size: 12px; 
  max-height: 200px; 
  overflow-y: auto;
}
</style>
</head>

<body>
<div class="container mt-4">
  <h3 class="page-title">⚡ curl → Locust 性能脚本生成器</h3>

  <!-- curl 输入 -->
  <div class="card p-3 mb-3">
    <label class="fw-bold">curl 请求（支持多个）</label>
    <textarea id="curl" class="form-control" rows="8" placeholder="可以粘贴多个curl命令，每个curl一行或几行"></textarea>
    <div class="mt-2">
      <button class="btn btn-sm btn-outline-primary" onclick="parseRequests()">解析请求</button>
      <small class="text-muted ms-2">点击解析后会显示所有请求的参数化配置表格</small>
      <button class="btn btn-sm btn-outline-info debug-btn" onclick="debugParams()">🔍 调试</button>
    </div>
  </div>

  <!-- 解析出的请求参数化表格 -->
  <div class="card p-3 mb-3" id="paramSection" style="display:none;">
    <label class="fw-bold">🧬 参数化配置</label>
    <div class="alert alert-info">
      <small>选择需要参数化的接口和字段，配置Faker生成规则</small>
    </div>
    
    <!-- 接口筛选 -->
    <div class="interface-filter">
      <label class="small fw-bold">筛选接口：</label>
      <select id="interfaceFilter" class="form-select form-select-sm" onchange="filterByInterface(this.value)">
        <option value="all">显示所有接口</option>
      </select>
    </div>
    
    <div id="paramTable"></div>
    <div id="paramDebugInfo" class="mt-2"></div>
  </div>

  <!-- 配置 -->
  <div class="card p-3">
    <div class="row g-2">
      <div class="col">
        <label class="small">并发用户</label>
        <input id="users" class="form-control" value="20" oninput="validateNumber(this)">
      </div>
      <div class="col">
        <label class="small">启动速率</label>
        <input id="rate" class="form-control" value="5" oninput="validateNumber(this)">
      </div>
      <div class="col">
        <label class="small">执行时间</label>
        <input id="duration" class="form-control" value="60" oninput="validateNumber(this)">
      </div>
      <div class="col">
        <label class="small">单位</label>
        <select id="duration_unit" class="form-select">
          <option value="s">秒</option>
          <option value="m">分钟</option>
          <option value="h">小时</option>
        </select>
      </div>
    </div>

    <!-- 并发模型 -->
    <div class="mt-3">
      <label class="small fw-bold">并发模型</label>
      <select id="model" class="form-select">
        <option value="fixed">固定</option>
        <option value="step">阶梯</option>
        <option value="ramp">斜坡</option>
        <option value="wave">波浪</option>
      </select>
    </div>

    <!-- 阶梯参数 -->
    <div class="row g-2 mt-2 step-config" id="step_config">
      <div class="col">
        <label class="small">起始并发</label>
        <input id="step_start" class="form-control" value="20" oninput="validateNumber(this)">
      </div>
      <div class="col">
        <label class="small">每阶梯增加</label>
        <input id="step_add" class="form-control" value="5" oninput="validateNumber(this)">
      </div>
      <div class="col">
        <label class="small">间隔(秒)</label>
        <input id="step_interval" class="form-control" value="10" oninput="validateNumber(this)">
      </div>
    </div>

    <!-- 生成按钮 -->
    <div class="mt-3">
      <button class="btn btn-primary w-100" onclick="generate()">
        🚀 生成 Locust 脚本
      </button>
      <button class="btn btn-sm btn-outline-secondary w-100 mt-2" onclick="testParams()">
        📋 测试参数传递
      </button>
    </div>
  </div>

  <!-- 图表 -->
  <div class="card p-3 mt-4">
    <label class="fw-bold">📈 并发负载实时预览</label>
    <canvas id="loadChart" height="140"></canvas>
  </div>

  <!-- 结果 -->
  <div class="card p-3 mt-4">
    <label class="fw-bold">生成的 Locust 脚本</label>
    <textarea id="result" class="form-control mt-2" rows="15" readonly></textarea>
    <div class="d-flex gap-2 mt-3">
      <button class="btn btn-success btn-sm" onclick="copyCode()">📋 复制</button>
      <button class="btn btn-outline-primary btn-sm" onclick="downloadCode()">⬇️ 下载</button>
      <button class="btn btn-outline-warning btn-sm" onclick="validateCode()">✅ 验证语法</button>
    </div>
    <div id="validationResult" class="mt-2"></div>
  </div>
</div>

<script>
/* ========= 防止 JS 中断 ========= */
function validateNumber(input){
  input.value = input.value.replace(/[^0-9]/g,'');
  if(input.value==='') input.value='0';
}

/* ========= Faker 方法列表（完整版） ========= */
const FAKER_METHODS = [
  {value: "name", text: "姓名"},
  {value: "phone_number", text: "手机号"},
  {value: "email", text: "邮箱"},
  {value: "address", text: "地址"},
  {value: "company", text: "公司名"},
  {value: "job", text: "职位"},
  {value: "random_int", text: "随机整数"},
  {value: "random_number", text: "随机数字"},
  {value: "uuid4", text: "UUID"},
  {value: "word", text: "单词"},
  {value: "sentence", text: "句子"},
  {value: "date", text: "日期"},
  {value: "date_time", text: "日期时间"},
  {value: "bothify", text: "模式替换"},
  {value: "lexify", text: "字母替换"},
  {value: "numerify", text: "数字替换"},
  {value: "user_name", text: "用户名"},
  {value: "password", text: "密码"},
  {value: "url", text: "URL"},
  {value: "ipv4", text: "IP地址"},
  {value: "country", text: "国家"},
  {value: "city", text: "城市"}
];

/* ========= 全局变量 ========= */
let parsedRequests = [];
let currentParams = {};
let currentInterfaceFilter = 'all';

/* ========= 调试函数 ========= */
function debugParams() {
  console.log("=== 调试参数化配置 ===");
  console.log("当前参数化配置:", JSON.stringify(currentParams, null, 2));
  console.log("解析的请求数量:", parsedRequests.length);
  
  const enabledCount = Object.values(currentParams).filter(p => p.enabled).length;
  const methodCount = Object.values(currentParams).filter(p => p.method).length;
  
  let debugInfo = `参数化统计：
  - 总配置数: ${Object.keys(currentParams).length}
  - 启用数: ${enabledCount}
  - 有方法数: ${methodCount}
  - 接口筛选: ${currentInterfaceFilter}`;
  
  console.log(debugInfo);
  
  // 显示参数化配置预览
  let previewHtml = '<div class="code-preview"><strong>当前参数化配置:</strong><br>';
  Object.entries(currentParams).forEach(([key, config]) => {
    if (config.enabled || config.method) {
      previewHtml += `${key}: {enabled: ${config.enabled}, method: '${config.method}'}<br>`;
    }
  });
  previewHtml += '</div>';
  
  document.getElementById('paramDebugInfo').innerHTML = previewHtml;
}

/* ========= 测试参数传递 ========= */
function testParams() {
  const paramConfigs = {};
  
  // 收集参数化配置
  Object.keys(currentParams).forEach(key => {
    const config = currentParams[key];
    if (config && (config.enabled || config.method)) {
      paramConfigs[key] = {
        enabled: config.enabled || false,
        method: config.method || ''
      };
    }
  });
  
  fetch("/test_params", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ params: paramConfigs })
  })
  .then(r => r.json())
  .then(data => {
    alert(`测试结果：
    总参数: ${data.params_count || 0}
    启用参数: ${data.enabled_count || 0}
    状态: ${data.message}`);
    console.log("测试返回:", data);
  });
}

/* ========= 解析请求 ========= */
function parseRequests(){
  fetch("/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ curl: curl.value })
  })
  .then(r=>r.json())
  .then(data=>{
    if(data.error){
      alert(data.error);
      return;
    }
    
    parsedRequests = data.requests;
    console.log("解析到的请求:", parsedRequests);
    
    // 合并新解析的参数，保留已有的配置
    const newParams = data.params || {};
    Object.keys(newParams).forEach(key => {
      if(currentParams[key]) {
        // 保留已有的配置
        newParams[key].enabled = currentParams[key].enabled || false;
        newParams[key].method = currentParams[key].method || '';
      } else {
        newParams[key].enabled = false;
        newParams[key].method = '';
      }
    });
    currentParams = newParams;
    
    // 显示参数化配置区域
    document.getElementById('paramSection').style.display = 'block';
    
    // 更新接口筛选下拉框
    updateInterfaceFilter();
    
    // 生成参数化配置表格
    renderParamTable();
    
    debugParams(); // 显示调试信息
  });
}

/* ========= 更新接口筛选下拉框 ========= */
function updateInterfaceFilter() {
  const filterSelect = document.getElementById('interfaceFilter');
  filterSelect.innerHTML = '<option value="all">显示所有接口</option>';
  
  parsedRequests.forEach((req, reqIndex) => {
    if(req.error) return;
    
    const label = `${req.method} ${req.path} (接口${reqIndex})`;
    filterSelect.innerHTML += `<option value="${reqIndex}">${label}</option>`;
  });
  
  filterSelect.value = currentInterfaceFilter;
}

/* ========= 按接口筛选 ========= */
function filterByInterface(interfaceIndex) {
  currentInterfaceFilter = interfaceIndex;
  renderParamTable();
}

/* ========= 渲染参数化表格 ========= */
function renderParamTable(){
  let html = '<table class="table table-sm table-bordered">';
  html += '<thead><tr><th>接口</th><th>字段位置</th><th>字段名</th><th>路径</th><th>当前值/示例</th><th>Faker方法</th><th>启用</th></tr></thead><tbody>';
  
  let hasRows = false;
  
  parsedRequests.forEach((req, reqIndex) => {
    // 如果设置了接口筛选，只显示选中的接口
    if(currentInterfaceFilter !== 'all' && reqIndex.toString() !== currentInterfaceFilter) {
      return;
    }
    
    if(req.error) {
      html += `<tr><td colspan="7" class="text-danger">接口${reqIndex}: ${req.error}</td></tr>`;
      return;
    }
    
    const fields = [];
    
    // Query参数
    if(req.query_params && Object.keys(req.query_params).length > 0){
      Object.entries(req.query_params).forEach(([key, value]) => {
        const paramKey = `${reqIndex}.params.${key}`;
        fields.push({
          type: 'query',
          key: key,                    // ✅ 显示字段名
          path: key,                    // ✅ 路径（这里和字段名一样）
          value: value,
          paramKey: paramKey,
          reqIndex: reqIndex
        });
      });
    }
    
    // JSON Body参数
    if(req.body_type === 'json' && req.body_value){
      if(typeof req.body_value === 'object'){
        flattenObject(req.body_value, fields, 'json', '', reqIndex);
      }
    }
    
    // Form Data参数
    if(req.body_type === 'data' && req.body_value){
      try{
        const params = new URLSearchParams(req.body_value);
        for(let [key, value] of params.entries()){
          const paramKey = `${reqIndex}.data.${key}`;
          fields.push({
            type: 'form',
            key: key,                    // ✅ 显示字段名
            path: key,                    // ✅ 路径（这里和字段名一样）
            value: value,
            paramKey: paramKey,
            reqIndex: reqIndex
          });
        }
      }catch(e){
        // 如果不是标准表单数据，作为原始数据展示
        const paramKey = `${reqIndex}.raw_data`;
        fields.push({
          type: 'raw',
          key: 'raw_data',              // ✅ 显示字段名
          path: 'raw_data',              // ✅ 路径
          value: req.body_value,
          paramKey: paramKey,
          reqIndex: reqIndex
        });
      }
    }
    
    // 为每个字段生成一行
    fields.forEach(field => {
      hasRows = true;
      const currentParam = currentParams[field.paramKey] || {};
      const isEnabled = currentParam.enabled || false;
      const selectedMethod = currentParam.method || '';
      
      html += `<tr class="param-row ${isEnabled ? 'param-enabled' : ''}" id="row-${field.paramKey.replace(/\./g, '-')}">`;
      html += `<td><small>${req.method} ${req.path}</small></td>`;
      html += `<td><code>${field.type}</code></td>`;
      html += `<td><code title="${field.paramKey}">${field.key}</code></td>`;  // ✅ 只显示字段名
      html += `<td><small title="${field.paramKey}">${field.path}</small></td>`;  // ✅ 新增路径列
      html += `<td><small title="${field.value}">${field.value.length > 20 ? field.value.substring(0,20)+'...' : field.value}</small></td>`;
      
      // Faker方法选择
      html += '<td><select class="form-select form-select-sm faker-select" style="width: 160px;" ';
      html += `onchange="onFakerSelectChange('${field.paramKey}', this.value)">`;
      html += '<option value="">-- 选择 --</option>';
      
      FAKER_METHODS.forEach(method => {
        const selected = selectedMethod === method.value ? 'selected' : '';
        html += `<option value="${method.value}" ${selected}>${method.text}</option>`;
      });
      html += '</select></td>';
      
      // 启用开关
      html += `<td><input type="checkbox" class="form-check-input param-enable" `;
      html += `onchange="onParamEnableChange('${field.paramKey}', this.checked)" ${isEnabled ? 'checked' : ''}></td>`;
      
      html += '</tr>';
    });
  });
  
  if(!hasRows && currentInterfaceFilter !== 'all') {
    html += `<tr><td colspan="7" class="text-center">该接口没有可参数化的字段</td></tr>`;
  } else if(!hasRows) {
    html += `<tr><td colspan="7" class="text-center">没有找到可参数化的字段</td></tr>`;
  }
  
  html += '</tbody></table>';
  document.getElementById('paramTable').innerHTML = html;
}

/* ========= ✅ 修复问题三：优化后的flattenObject函数 ========= */
function flattenObject(obj, fields, type, prefix = '', reqIndex = 0){
  if(obj === null || obj === undefined) return;

  // 处理数组
  if(Array.isArray(obj)){
    obj.forEach((item, idx) => {
      const newPrefix = prefix ? `${prefix}[${idx}]` : `[${idx}]`;
      const paramKey = `${reqIndex}.json.${newPrefix}`;

      if(typeof item === 'object' && item !== null){
        flattenObject(item, fields, type, newPrefix, reqIndex);
      } else {
        // ✅ 优化：只显示当前字段名，不显示完整路径
        const fieldName = `[${idx}]`;  // 数组索引作为字段名
        fields.push({
          type: type,
          key: fieldName,              // ✅ 只显示字段名：[0], [1]
          path: newPrefix,             // ✅ 完整路径：user.list[0]
          value: String(item),
          paramKey: paramKey,
          reqIndex: reqIndex
        });
      }
    });
    return;
  }

  // 处理对象
  if(typeof obj === 'object'){
    Object.entries(obj).forEach(([key, value]) => {
      const newPrefix = prefix ? `${prefix}.${key}` : key;
      const paramKey = `${reqIndex}.json.${newPrefix}`;

      if(typeof value === 'object' && value !== null){
        flattenObject(value, fields, type, newPrefix, reqIndex);
      } else {
        fields.push({
          type: type,
          key: key,                    // ✅ 只显示字段名：name, age
          path: newPrefix,             // ✅ 完整路径：user.name, user.list[0].name
          value: String(value),
          paramKey: paramKey,
          reqIndex: reqIndex
        });
      }
    });
  }
}

/* ========= 事件处理 ========= */
function onFakerSelectChange(paramKey, value){
  console.log(`选择Faker方法: ${paramKey} = ${value}`);
  
  if(!currentParams[paramKey]){
    currentParams[paramKey] = {};
  }
  currentParams[paramKey].method = value;
  
  // 自动启用
  currentParams[paramKey].enabled = true;
  
  // 更新行样式
  const rowId = 'row-' + paramKey.replace(/\./g, '-');
  const row = document.getElementById(rowId);
  if(row){
    row.classList.add('param-enabled');
    const checkbox = row.querySelector('.param-enable');
    if(checkbox) checkbox.checked = true;
  }
  
  debugParams(); // 更新调试信息
}

function onParamEnableChange(paramKey, enabled){
  console.log(`启用/禁用参数: ${paramKey} = ${enabled}`);
  
  if(!currentParams[paramKey]){
    currentParams[paramKey] = {};
  }
  currentParams[paramKey].enabled = enabled;
  
  // 如果禁用，清空方法选择
  if(!enabled){
    currentParams[paramKey].method = '';
    
    // 清空下拉框选择
    const rowId = 'row-' + paramKey.replace(/\./g, '-');
    const row = document.getElementById(rowId);
    if(row){
      const select = row.querySelector('.faker-select');
      if(select) select.value = '';
    }
  }
  
  // 更新行样式
  const rowId = 'row-' + paramKey.replace(/\./g, '-');
  const row = document.getElementById(rowId);
  if(row){
    if(enabled){
      row.classList.add('param-enabled');
    } else {
      row.classList.remove('param-enabled');
    }
  }
  
  debugParams(); // 更新调试信息
}

/* ========= 生成 ========= */
function generate(){
  // 收集参数化配置
  const paramConfigs = {};
  
  // 遍历所有已配置的参数
  Object.keys(currentParams).forEach(key => {
    const config = currentParams[key];
    if (config && (config.enabled || config.method)) {
      paramConfigs[key] = {
        enabled: config.enabled || false,
        method: config.method || ''
      };
    }
  });
  
  console.log("发送的参数化配置:", JSON.stringify(paramConfigs, null, 2));
  
  // 确保发送所有必要的参数
  const postData = {
    curl: curl.value,
    users: users.value,
    rate: rate.value,
    duration: duration.value,
    duration_unit: duration_unit.value,
    model: model.value,
    step_start: step_start.value,
    step_add: step_add.value,
    step_interval: step_interval.value,
    params: paramConfigs
  };
  
  fetch("/",{
    method:"POST",
    headers:{ "Content-Type":"application/json" },
    body: JSON.stringify(postData)
  })
  .then(r=>r.json())
  .then(d=>{
    if(d.error){ 
      alert("生成错误: " + d.error); 
      return; 
    }
    result.value = d.code;
    
    // 显示生成信息
    const enabledCount = Object.values(paramConfigs).filter(p => p.enabled).length;
    document.getElementById('validationResult').innerHTML = 
      `<div class="alert alert-success small">✅ 生成成功！已启用 ${enabledCount} 个参数化字段</div>`;
  });
}

/* ========= 验证代码语法 ========= */
function validateCode() {
  const code = result.value;
  if(!code) {
    document.getElementById('validationResult').innerHTML = 
      `<div class="alert alert-warning">⚠️ 请先生成代码</div>`;
    return;
  }
  
  fetch("/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code: code })
  })
  .then(r => r.json())
  .then(data => {
    if(data.valid) {
      document.getElementById('validationResult').innerHTML = 
        `<div class="alert alert-success">✅ 语法验证通过！可以运行此Locust脚本。</div>`;
    } else {
      document.getElementById('validationResult').innerHTML = 
        `<div class="alert alert-danger">❌ 语法错误: ${data.error}</div>`;
    }
  });
}

/* ========= 并发模型图表 ========= */
let chart;
function totalSeconds(){
  let d = +duration.value || 60;
  if(duration_unit.value==='m') d*=60;
  if(duration_unit.value==='h') d*=3600;
  return d;
}

function buildSeries(){
  const pts = 40;
  const t = totalSeconds();
  const base = +users.value||1;
  const start = +step_start.value||base;
  const add = +step_add.value||1;
  const interval = +step_interval.value||10;

  const labels=[], data=[];
  for(let i=0;i<=pts;i++){
    const sec = t/pts*i;
    labels.push(sec.toFixed(0)+'s');

    let v=base;
    if(model.value==='step'){
      v = start + Math.floor(sec/interval)*add;
    } else if(model.value==='ramp'){
      v = base + (sec/t)*base;
    } else if(model.value==='wave'){
      v = base + Math.sin(sec/t*2*Math.PI)*base/2;
    }
    data.push(Math.max(0,Math.round(v)));
  }
  return {labels,data};
}

function render(){
  const s = buildSeries();
  const peak = Math.max(...s.data);
  const last = s.data[s.data.length-1];

  if(chart) chart.destroy();
  chart = new Chart(loadChart,{
    type:'line',
    data:{
      labels:s.labels,
      datasets:[
        {label:'并发用户',data:s.data,fill:true},
        {label:'峰值',data:s.data.map(()=>peak),borderDash:[5,5],pointRadius:0},
        {label:'最终',data:s.data.map(()=>last),borderDash:[2,2],pointRadius:0}
      ]
    },
    options:{responsive:true,plugins:{legend:{position:'top'}}}
  });
}

/* ========= 复制 / 下载 ========= */
function copyCode(){
  if(!result.value) return;
  navigator.clipboard.writeText(result.value);
  alert("已复制到剪贴板");
}

function downloadCode(){
  if(!result.value) return;
  const blob = new Blob([result.value],{type:"text/x-python"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "locustfile.py";
  a.click();
}

/* ========= 初始化 ========= */
['users','duration','step_start','step_add','step_interval']
.forEach(id=>document.getElementById(id).addEventListener('input',render));
duration_unit.addEventListener('change',render);
model.addEventListener('change',()=>{
  step_config.classList.toggle('enabled',model.value==='step');
  render();
});

render();
</script>
<!-- 看板娘 Live2D -->
<script src="https://xiaopeng.love/js/L2Dwidget.min.js" defer></script>

<script defer>
document.addEventListener('DOMContentLoaded', function () {
    if (typeof L2Dwidget === 'undefined') return;

    L2Dwidget.init({
        model: {
            jsonPath: "https://unpkg.com/live2d-widget-model-koharu@1.0.5/assets/koharu.model.json",
            scale: 1
        },
        display: {
            position: "right",
            width: 150,
            height: 300,
            hOffset: 0,
            vOffset: -20
        },
        mobile: {
            show: true,
            scale: 0.5
        },
        react: {
            opacityDefault: 0.7,
            opacityOnHover: 0.2
        }
    });
});
</script>
</body>
</html>
"""

# ================= 工具函数 =================
def split_curls(text):
    """分割多个curl命令"""
    blocks = []
    current = []
    
    for line in text.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        
        if line.lstrip().startswith("curl "):
            if current:
                blocks.append("\n".join(current))
                current = []
        
        current.append(line)
    
    if current:
        blocks.append("\n".join(current))
    
    return blocks

def parse_curl(curl_str):
    """解析单个curl命令"""
    curl_str = curl_str.replace('\\"', '"').replace("\\'", "'")
    tokens = shlex.split(curl_str, posix=True)
    it = iter(tokens)
    
    method = "GET"
    headers = {}
    cookies = []
    body = None
    original_url = None
    
    for t in it:
        if t in ("-X", "--request"):
            method = next(it).upper()
        elif t in ("-H", "--header"):
            h = next(it)
            if ":" in h:
                k, v = h.split(":", 1)
                # ⚠️ 对header值进行清理，移除多余的转义
                v = v.strip()
                # 清理多余的转义字符
                v = v.replace('\\"', '"').replace("\\'", "'")
                headers[k.strip()] = v
        elif t in ("-b", "--cookie"):
            cookies.append(next(it))
        elif t in ("--data", "--data-raw", "-d"):
            body = next(it)
        elif t.startswith("http"):
            original_url = t
    
    if not original_url:
        raise ValueError("未找到URL")
    
    parsed_url = urlparse(original_url)
    
    if cookies:
        headers["Cookie"] = "; ".join(cookies)
    
    if body and method == "GET":
        method = "POST"
    
    query_params = {}
    if parsed_url.query:
        try:
            q = parse_qs(parsed_url.query)
            query_params = {k: v[0] if v else "" for k, v in q.items()}
        except Exception:
            pass
    
    return method, original_url, parsed_url, headers, body, query_params

def detect_body_type(body, headers):
    """检测body类型"""
    if not body:
        return None, None
    
    cleaned_body = body.strip()
    cleaned_body = cleaned_body.replace('\\"', '"').replace("\\'", "'")
    
    content_type = None
    for key, value in headers.items():
        if key.lower() == 'content-type':
            content_type = value.lower()
            break
    
    if content_type:
        if 'application/json' in content_type:
            try:
                parsed = json.loads(cleaned_body)
                return 'json', parsed
            except json.JSONDecodeError:
                return _try_repair_json(cleaned_body)
        elif 'application/x-www-form-urlencoded' in content_type:
            return 'data', cleaned_body
        else:
            return 'data', cleaned_body
    
    return _auto_detect_body_type(cleaned_body)

def _try_repair_json(body_str):
    """修复JSON"""
    if not body_str:
        return 'data', body_str
    
    try:
        repaired = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', body_str)
        parsed = json.loads(repaired)
        return 'json', parsed
    except json.JSONDecodeError:
        pass
    
    try:
        repaired = body_str.replace("'", '"')
        parsed = json.loads(repaired)
        return 'json', parsed
    except json.JSONDecodeError:
        pass
    
    return 'data', body_str

def _auto_detect_body_type(body_str):
    """自动检测body类型"""
    if not body_str:
        return None, None
    
    trimmed = body_str.strip()
    
    if (trimmed.startswith('{') and trimmed.endswith('}')) or \
       (trimmed.startswith('[') and trimmed.endswith(']')):
        try:
            parsed = json.loads(trimmed)
            return 'json', parsed
        except json.JSONDecodeError:
            return _try_repair_json(trimmed)
    
    if '=' in trimmed and not trimmed.startswith(('http://', 'https://')):
        if '&' in trimmed or re.search(r'[^=&]+=[^=&]+(?:&[^=&]+=[^=&]+)+', trimmed):
            return 'data', trimmed
        elif re.match(r'^[a-zA-Z0-9_.-]+=[^=]*$', trimmed):
            return 'data', trimmed
    
    return 'data', trimmed

# ================= Faker表达式生成函数 =================
def generate_faker_expression(method):
    """根据方法名生成Faker表达式（返回FakerExpr标记对象）"""
    if method == 'random_int':
        return FakerExpr("fake.random_int(min=1, max=10000)")
    elif method == 'random_number':
        return FakerExpr("fake.random_number(digits=6)")
    elif method == 'uuid4':
        return FakerExpr("str(fake.uuid4())")
    elif method == 'bothify':
        return FakerExpr("fake.bothify(text='??##??')")
    elif method == 'lexify':
        return FakerExpr("fake.lexify(text='???')")
    elif method == 'numerify':
        return FakerExpr("fake.numerify(text='###')")
    elif method == 'date':
        return FakerExpr("fake.date()")
    elif method == 'date_time':
        return FakerExpr("fake.date_time()")
    elif method == 'password':
        return FakerExpr("fake.password(length=12)")
    elif method == 'user_name':
        return FakerExpr("fake.user_name()")
    elif method == 'url':
        return FakerExpr("fake.url()")
    elif method == 'ipv4':
        return FakerExpr("fake.ipv4()")
    else:
        return FakerExpr(f"fake.{method}()")

# ================= ✅ 修复问题一：优化后的apply_parametrize函数 =================
def apply_parametrize(obj, param_rules, base_path=""):
    """
    ✅ 修复关键问题：当前路径优先命中，命中后立即返回Faker表达式
    """
    if not param_rules:
        return obj

    # ⭐ 关键：当前路径优先命中
    if base_path in param_rules:
        rule = param_rules[base_path]
        if rule.get("enabled") and rule.get("method"):
            return generate_faker_expression(rule["method"])

    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            path = f"{base_path}.{key}" if base_path else key
            result[key] = apply_parametrize(value, param_rules, path)
        return result

    if isinstance(obj, list):
        result = []
        for i, item in enumerate(obj):
            path = f"{base_path}[{i}]" if base_path else f"[{i}]"
            result.append(apply_parametrize(item, param_rules, path))
        return result

    return obj

# ================= ✅ 修复问题一：优化后的Form-data参数化函数 =================
def apply_parametrize_to_form_data(form_data, param_rules, req_index):
    """
    ✅ 修复：使用 i.data.key 形式进行匹配
    """
    try:
        result = {}
        pairs = form_data.split("&")
        for pair in pairs:
            if "=" not in pair:
                continue
            key, value = pair.split("=", 1)

            full_key = f"{req_index}.data.{key}"

            if full_key in param_rules:
                rule = param_rules[full_key]
                if rule.get("enabled") and rule.get("method"):
                    result[key] = generate_faker_expression(rule["method"])
                else:
                    result[key] = value
            else:
                result[key] = value

        return result
    except Exception:
        return form_data

# ================= 格式化函数 =================
def format_python_value(value, indent=12, max_line_length=80):
    """格式化Python值"""
    # ✅ 首先检查是否是FakerExpr对象
    if isinstance(value, FakerExpr):
        return str(value)
    
    # 检查是否是字符串但包含fake.开头
    if isinstance(value, str) and value.startswith('fake.'):
        return value
    
    # 检查是否是字典（处理form-data返回的dict）
    if isinstance(value, dict):
        items = []
        for k, v in value.items():
            formatted_key = f'"{k}"' if isinstance(k, str) else repr(k)
            formatted_val = format_python_value(v, indent + 4, max_line_length)
            items.append(f'{formatted_key}: {formatted_val}')
        
        single_line = '{' + ', '.join(items) + '}'
        if len(single_line) <= max_line_length - indent:
            return single_line
        
        current_indent = ' ' * indent
        next_indent = ' ' * (indent + 4)
        return '{\n' + ',\n'.join(f'{next_indent}{item}' for item in items) + f'\n{current_indent}}}'
    
    # 检查是否是列表
    if isinstance(value, list):
        formatted_items = [format_python_value(item, indent + 4, max_line_length) for item in value]
        single_line = '[' + ', '.join(formatted_items) + ']'
        if len(single_line) <= max_line_length - indent:
            return single_line
        
        current_indent = ' ' * indent
        next_indent = ' ' * (indent + 4)
        return '[\n' + ',\n'.join(f'{next_indent}{item}' for item in formatted_items) + f'\n{current_indent}]'
    
    # 检查是否是字符串 - ⚠️ 修复字符串处理逻辑
    if isinstance(value, str):
        # 检查字符串中是否包含双引号
        if '"' in value:
            # 如果包含双引号，使用单引号包裹
            if "'" not in value:
                # 字符串中不包含单引号，使用单引号
                escaped = value.replace('\\', '\\\\')
                # 处理双引号转义
                escaped = escaped.replace('"', '\\"')
                return f"'{escaped}'"
            else:
                # 字符串中既包含单引号又包含双引号，使用三双引号
                escaped = value.replace('\\', '\\\\')
                escaped = escaped.replace('"""', '\\"\\"\\"')
                if '\n' in value:
                    return f'"""{escaped}"""'
                elif len(escaped) + 6 > max_line_length - indent:
                    return f'"""{escaped}"""'
                else:
                    return f'"{escaped}"'
        else:
            # 不包含双引号，直接使用双引号
            escaped = value.replace('\\', '\\\\').replace('"', '\\"')
            if '\n' in value:
                return f'"""{value}"""'
            elif len(escaped) + 2 > max_line_length - indent:
                return f'"""{value}"""'
            else:
                return f'"{escaped}"'
    
    # 其他基本类型
    if isinstance(value, (int, float, bool)) or value is None:
        return repr(value)
    
    return repr(value)

# ================= 主生成函数 =================
def gen_locust_multi(
    curls,
    users,
    rate,
    duration,
    duration_unit,
    host_override=None,
    model="fixed",
    step_start=20,
    step_add=5,
    step_interval=10,
    params=None
):
    """生成Locust脚本"""
    print(f"🔧 收到参数化配置: {params}")
    
    # 基础参数
    duration_seconds = int(duration)
    if duration_unit == "m":
        duration_seconds *= 60
    elif duration_unit == "h":
        duration_seconds *= 3600
    
    users = max(1, int(users) if str(users).isdigit() else 1)
    rate = max(1, int(rate) if str(rate).isdigit() else 1)
    
    # 解析所有请求
    parsed_requests = []
    for curl in curls:
        try:
            method, original_url, parsed_url, headers, body, query_params = parse_curl(curl)
            body_type, body_value = detect_body_type(body, headers)
            
            parsed_requests.append({
                'method': method,
                'url': original_url,
                'parsed_url': parsed_url,
                'headers': headers,
                'body': body,
                'body_type': body_type,
                'body_value': body_value,
                'query_params': query_params,
                'path': parsed_url.path or "/"
            })
        except Exception as e:
            parsed_requests.append({
                'error': str(e)
            })
    
    # 确定host
    final_host = None
    for req in parsed_requests:
        if 'parsed_url' in req:
            parsed_url = req['parsed_url']
            host = f"{parsed_url.scheme}://{parsed_url.netloc}"
            if host_override:
                host = host_override
            final_host = final_host or host
            break
    
    if not final_host:
        final_host = "http://localhost"
    
    # 生成任务
    tasks = []
    for i, req in enumerate(parsed_requests):
        if 'error' in req:
            tasks.append(f"""
    @task
    def api_{i}(self):
        raise Exception("{req['error']}")
""")
            continue
        
        method = req['method']
        path = req['parsed_url'].path or "/"
        api_name = req['path']
        if len(api_name) > 50:
            api_name = api_name[:47] + "..."
        
        args = []
        
        # ✅ 处理查询参数
        if req['query_params']:
            processed_params = {}
            for key, value in req['query_params'].items():
                param_key = f"{i}.params.{key}"
                if params and param_key in params:
                    rule = params[param_key]
                    if rule.get('enabled', False) and rule.get('method'):
                        processed_params[key] = generate_faker_expression(rule['method'])
                    else:
                        processed_params[key] = value
                else:
                    processed_params[key] = value
            
            args.append(f"params={format_python_value(processed_params)}")
        
        # 处理headers
        if req['headers']:
            processed_headers = req['headers'].copy()
            if req['body_type'] == "json":
                if "Content-Type" in processed_headers and "application/json" not in processed_headers["Content-Type"]:
                    del processed_headers["Content-Type"]
            args.append(f"headers={format_python_value(processed_headers)}")
        
        # ✅ 处理body
        if req['body'] and method.upper() != "GET":
            if req['body_type'] == "json" and req['body_value']:
                # ✅ 提取JSON参数规则
                json_param_rules = {}
                if params:
                    for key, rule in params.items():
                        if key.startswith(f"{i}.json."):
                            # ✅ 关键：直接使用前端传来的完整路径，不进行转换
                            pure_key = key.replace(f"{i}.json.", "", 1)
                            json_param_rules[pure_key] = rule
                
                print(f"JSON参数规则: {json_param_rules}")
                processed_body = apply_parametrize(req['body_value'], json_param_rules)
                print(f"处理后的JSON: {processed_body}")
                args.append(f"json={format_python_value(processed_body)}")
            elif req['body_type'] == "data":
                # ✅ 修复问题一：不再提取form_param_rules，直接传递params
                # 因为apply_parametrize_to_form_data需要完整的i.data.key格式
                print(f"Form-data原始参数: {req['body_value']}")
                # ✅ 关键修复：直接调用优化后的函数
                processed_body = apply_parametrize_to_form_data(
                    req['body_value'],
                    params,  # ✅ 传递完整的params
                    i        # ✅ 传递当前请求索引
                )
                print(f"处理后的表单: {processed_body}")
                args.append(f"data={format_python_value(processed_body)}")
            else:
                args.append(f'data="{req["body"]}"')
        
        args.append(f'name="{api_name}"')
        args.append("timeout=10")
        
        tasks.append(f"""
    @task
    def api_{i}(self):
        \"\"\"{method} {api_name}\"\"\"
        self.client.{method.lower()}(
            "{path}",
            {", ".join(args)}
        )
""")
    
    # 生成LoadTestShape
    import_line = "from locust import HttpUser, task, between"
    if model != "fixed":
        import_line += ", LoadTestShape"
    import_line += "\nfrom faker import Faker\nfake = Faker('zh_CN')"
    
    shape_code = ""
    run_cmd = ""
    config_info = ""
    mode_name = "固定并发"
    
    # 统计参数化字段数量
    enabled_param_count = 0
    if params:
        enabled_param_count = sum(1 for rule in params.values() 
                                if rule.get('enabled', False))
    
    if model == "fixed":
        run_cmd = f"locust -f locustfile.py --headless --host={final_host} -u {users} -r {rate} -t {duration}{duration_unit} --csv=result --html report.html"
        config_info = f"# - 并发用户数: {users}\n# - 启动速率: {rate} 用户/秒\n# - 执行时间: {duration}{duration_unit}"
    
    elif model == "step":
        mode_name = "阶梯并发"
        shape_code = f"""
class StepLoadShape(LoadTestShape):
    step_time = {step_interval}
    step_load = {step_add}
    start_users = {step_start}
    spawn_rate = {rate}
    time_limit = {duration_seconds}

    def tick(self):
        t = self.get_run_time()
        if t > self.time_limit:
            return None
        users = self.start_users + int(t // self.step_time) * self.step_load
        users = min(users, 10000)
        return users, self.spawn_rate
"""
        run_cmd = f"locust -f locustfile.py --headless --host={final_host} --csv=result --html report.html"
    
    elif model == "ramp":
        mode_name = "线性斜坡"
        ramp_start = max(1, rate)
        ramp_end = max(1, users)
        shape_code = f"""
class RampLoadShape(LoadTestShape):
    spawn_rate = {rate}
    time_limit = {duration_seconds}

    def tick(self):
        t = self.get_run_time()
        if t > self.time_limit:
            return None
        users = {ramp_start} + ({ramp_end} - {ramp_start}) * (t / self.time_limit)
        return int(users), self.spawn_rate
"""
        run_cmd = f"locust -f locustfile.py --headless --host={final_host} --csv=result --html report.html"
    
    elif model == "wave":
        mode_name = "波浪并发"
        wave_min = max(1, int(users * 0.5))
        wave_max = max(wave_min + 1, int(users * 1.5))
        wave_period = max(10, duration_seconds // 4)
        shape_code = f"""
import math

class WaveLoadShape(LoadTestShape):
    min_users = {wave_min}
    max_users = {wave_max}
    period = {wave_period}
    spawn_rate = {rate}
    time_limit = {duration_seconds}

    def tick(self):
        t = self.get_run_time()
        if t > self.time_limit:
            return None
        mid = (self.min_users + self.max_users) / 2
        amp = (self.max_users - self.min_users) / 2
        users = mid + amp * math.sin(2 * math.pi * t / self.period)
        return int(max(0, users)), self.spawn_rate
"""
        run_cmd = f"locust -f locustfile.py --headless --host={final_host} --csv=result --html report.html"
    
    # 生成最终代码
    return f"""{import_line}

{shape_code}

class ApiUser(HttpUser):
    host = "{final_host}"
    wait_time = between(1, 2)
{''.join(tasks)}

# ===================== 压测运行说明 =====================
# 📊 核心信息
# - 接口数量: {len(curls)} 个
# - 压测模式: {mode_name}
{config_info}
# - 参数化字段: {enabled_param_count} 个字段使用Faker生成
# - Faker语言: 中文(zh_CN)

# 🚀 运行命令
# 1️⃣ 无头模式（自动运行，生成报表）
# {run_cmd}

# 2️⃣ Web UI 模式（推荐）
# locust -f locustfile.py --host {final_host}

# 📈 查看结果
# - CSV: result_stats.csv / result_requests.csv
# - HTML: report.html

# 💡 提示
# 1. 确保已安装依赖
# 2. 首次运行前建议测试脚本: python -m py_compile locustfile.py
# 3. 参数化字段会在每次请求时动态生成新数据
"""

# ================= ✅ 修复问题二：简化的解析函数 =================
@app.route("/parse", methods=["POST"])
def parse_requests():
    """解析curl命令，返回可参数化的字段"""
    try:
        data = request.get_json()
        curls = split_curls(data.get("curl", ""))
        
        if not curls:
            return jsonify({"error": "未检测到有效的 curl 命令"})
        
        parsed_requests = []
        all_params = {}
        
        for i, curl in enumerate(curls):
            try:
                method, original_url, parsed_url, headers, body, query_params = parse_curl(curl)
                body_type, body_value = detect_body_type(body, headers)
                
                request_info = {
                    'index': i,
                    'method': method,
                    'url': original_url,
                    'parsed_url': parsed_url._asdict() if parsed_url else None,
                    'headers': headers,
                    'body': body,
                    'body_type': body_type,
                    'body_value': body_value,
                    'query_params': query_params,
                    'path': parsed_url.path if parsed_url else "/"
                }
                
                parsed_requests.append(request_info)
                
                # ================================
                # 收集可参数化的字段
                # ================================

                # ---------- 1️⃣ Query 参数 ----------
                if query_params:
                    for key, value in query_params.items():
                        param_key = f"{i}.params.{key}"
                        all_params[param_key] = {
                            'field': key,
                            'type': 'query',
                            'value': str(value),
                            'enabled': False,
                            'method': ''
                        }

                # ---------- 2️⃣ JSON Body ----------
                # ⚠️ 不在后端重新 flatten JSON
                # 前端 flattenObject 已经生成完整 json 参数路径
                # 后端这里只标记存在 JSON body 即可
                if body_type == 'json' and body_value:
                    # 不做任何字段收集，避免路径不一致
                    pass

                # ---------- 3️⃣ Form Data ----------
                if body_type == 'data' and body_value:
                    try:
                        pairs = body_value.split('&')
                        for pair in pairs:
                            if '=' not in pair:
                                continue
                            key, value = pair.split('=', 1)
                            param_key = f"{i}.data.{key}"
                            all_params[param_key] = {
                                'field': key,
                                'type': 'form',
                                'value': value,
                                'enabled': False,
                                'method': ''
                            }
                    except Exception:
                        # 极端兜底：无法解析的 raw form-data
                        param_key = f"{i}.raw_data"
                        all_params[param_key] = {
                            'field': 'raw_data',
                            'type': 'raw',
                            'value': body_value[:100] + ('...' if len(body_value) > 100 else ''),
                            'enabled': False,
                            'method': ''
                        }
                        
            except Exception as e:
                parsed_requests.append({
                    'index': i,
                    'error': str(e)
                })
        
        print(f"📋 解析完成: {len(parsed_requests)}个请求, {len(all_params)}个可参数化字段")
        
        return jsonify({
            'requests': parsed_requests,
            'params': all_params
        })
        
    except Exception as e:
        print(f"❌ 解析错误: {str(e)}")
        return jsonify({"error": str(e)})

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            d = request.get_json()
            print(f"📥 收到生成请求，参数: {json.dumps(d, indent=2, ensure_ascii=False)}")
            
            curls = split_curls(d.get("curl", ""))
            
            if not curls:
                return jsonify({"error": "未检测到有效的 curl 命令"})
            
            params = d.get("params", {})
            print(f"📋 收到的参数化配置数量: {len(params)}")
            for key, rule in params.items():
                print(f"  {key}: enabled={rule.get('enabled')}, method={rule.get('method')}")
            
            code = gen_locust_multi(
                curls=curls,
                users=d["users"],
                rate=d["rate"],
                duration=d["duration"],
                duration_unit=d["duration_unit"],
                host_override=d.get("host"),
                model=d.get("model", "fixed"),
                step_start=int(d.get("step_start", 20)),
                step_add=int(d.get("step_add", 5)),
                step_interval=int(d.get("step_interval", 10)),
                params=params
            )
            
            app.generated_code = code
            return jsonify({"code": code})
        except Exception as e:
            print(f"❌ 生成错误: {str(e)}")
            return jsonify({"error": str(e)})
    
    return render_template_string(HTML)

@app.route("/test_params", methods=["POST"])
def test_params():
    """测试参数化配置接收"""
    try:
        data = request.get_json()
        print("🔍 接收到的测试数据:", json.dumps(data, indent=2, ensure_ascii=False))
        
        params = data.get("params", {})
        print("📋 参数化配置详情:")
        enabled_count = 0
        for key, rule in params.items():
            enabled = rule.get('enabled', False)
            method = rule.get('method', '')
            print(f"  {key}: enabled={enabled}, method={method}")
            if enabled:
                enabled_count += 1
        
        return jsonify({
            "message": "参数接收成功",
            "params_count": len(params),
            "enabled_count": enabled_count
        })
    except Exception as e:
        print(f"❌ 测试错误: {str(e)}")
        return jsonify({"error": str(e)})

@app.route("/validate", methods=["POST"])
def validate_code():
    """验证生成的Python代码语法"""
    try:
        import ast
        data = request.get_json()
        code = data.get("code", "")
        
        if not code:
            return jsonify({"valid": False, "error": "代码为空"})
        
        # 尝试解析Python代码
        ast.parse(code)
        
        return jsonify({"valid": True, "message": "语法正确"})
    except SyntaxError as e:
        return jsonify({"valid": False, "error": f"第{e.lineno}行: {e.msg}"})
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)})

@app.route("/download")
def download():
    return send_file(
        BytesIO(app.generated_code.encode()),
        as_attachment=True,
        download_name="locustfile.py"
    )

if __name__ == "__main__":
    print("=" * 60)
    print("⚡ curl → Locust 性能脚本生成器")
    print("访问 http://127.0.0.1:8899")
    print("=" * 60)
    app.run(port=8899, host="0.0.0.0", debug=False)
