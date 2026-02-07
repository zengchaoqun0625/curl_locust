# 🚀 curl → Locust  
> Paste curl, generate a runnable Locust load-testing script in seconds.

一个把 **curl 请求直接转换为 Locust 压测脚本** 的 Web 工具，  
目标是：**减少重复劳动，让性能测试更确定、更真实、更可交付。**

---

## ✨ 为什么做这个项目？

在真实项目中，性能测试经常遇到这些问题 👇

- 已经有 **curl**，却还要重新手写 Locust  
- JMeter 配置繁琐，维护成本极高  
- 参数写死，压出来的数据毫无参考价值  
- 并发配置靠感觉，结果只能跑完才知道  

> **curl 已经包含了所有请求信息，  
> 那为什么不能直接生成压测脚本？**

这个项目，就是这个问题的答案。

---

## 🧩 Version 1：先解决「能跑」

第一版的目标非常明确 👇  

> 🎯 **curl → 可运行的 Locust 脚本**

### ✅ 已实现能力

- 支持粘贴 **多个 curl**
- 自动解析 `method / headers / body`
- 智能识别 `JSON / Form / Query`
- 一键生成 **可直接运行的 Locust 脚本**

### ⏱️ 使用效果

> 从 curl 到 Locust，只需要 **5 秒**

#### 示例界面

![](https://fastly.jsdelivr.net/gh/bucketio/img7@main/2026/01/31/1769845731626-5f2e2c2d-53a9-40c6-84e7-b600c64cb4ac.png)

![](https://fastly.jsdelivr.net/gh/bucketio/img0@main/2026/01/31/1769845752653-b83dd8cc-c049-4b9f-8d2d-32d6ed9e1513.png)

![](https://fastly.jsdelivr.net/gh/bucketio/img3@main/2026/01/31/1769845660675-4bab1acd-3be4-468f-a32e-0898a96a0297.png)


> 第一版已经比绝大多数**手写压测脚本**快得多。

---

## ⚠️ Version 1 的局限

虽然「能跑」，但在真实项目中仍然存在明显问题 👇

- 参数全部写死（假数据）
- 并发只能手填数字（不可预期）
- 压测行为不可视（容易翻车）

👉 **能跑 ≠ 真正的压测**

---

## 🔥 Version 2：像一个真正的压测工具

第二版的目标是 👇

> 🎯 **生成的脚本，看起来就像是「认真写过的」**

---

## 🎯 1️⃣ 参数化（Faker）  
### 不再压「假数据」

- 自动解析接口字段
- 区分 `JSON / Query / Form`
- 可视化选择 Faker 规则
- 无需写代码即可完成参数化

示例 👇

- `email` → `Faker.email`
- `username` → `Faker.name`

#### 参数化配置界面

<img width="2768" height="972" alt="image" src="https://github.com/user-attachments/assets/dab33a63-1090-4942-a07b-d25fa82e09c2" />


---

## 📈 2️⃣ 并发模型可视化  
### 先看到，再去压

支持多种并发模型 👇

- 固定并发
- 阶梯并发
- 斜坡并发
- 波浪并发

并提供 👇

- 实时并发曲线预览
- 峰值 / 最终并发一眼可见

#### 并发曲线预览

<img width="2880" height="1462" alt="image" src="https://github.com/user-attachments/assets/34f11faa-04ea-42f4-8dbb-825b5e1a1b93" />


> 从「拍脑袋配并发」  
> 变成「看着曲线做决定」

---

## 🧠 3️⃣ Locust 脚本语法校验  
### 把失败挡在运行之前

- 生成后立即校验 Locust 语法
- 错误直接提示
- 校验通过才允许使用

页面反馈 👇

> ✅ **语法验证通过！可以运行此 Locust 脚本**

#### 校验提示示例

<img width="2880" height="1174" alt="image" src="https://github.com/user-attachments/assets/7f0ebd90-4cfe-41ea-a766-ebf68339f11a" />


---

## 🔄 完整工作流

```text
Paste curl
   ↓
Parse request & params
   ↓
Parameterize fields (Faker)
   ↓
Configure load model
   ↓
Preview concurrency curve
   ↓
Generate Locust script
   ↓
Syntax validation
   ↓
Copy / Download / Run

## 最后也希望大家能提出更多使用上的优化，多多交流！
