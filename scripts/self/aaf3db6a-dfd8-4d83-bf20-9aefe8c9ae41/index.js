// ==UserScript==
// @name         Kirka.io 汉化
// @namespace    https://kirka.io/
// @version      12.1
// @description  支持油猴菜单开关、全量词库与动态解析
// @author       ACG-Q
// @match        *://kirka.io/*
// @match        *://*.kirka.io/*
// @grant        GM_registerMenuCommand
// @grant        GM_setValue
// @grant        GM_getValue
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    // ==========================================
    // 1. 夺回原生控制台
    // ==========================================
    try {
        const i = document.createElement('iframe');
        i.style.display = 'none';
        document.documentElement.appendChild(i);
        window.console = i.contentWindow.console;
        console.log("%c[Kirka汉化] ✅ 原生控制台已夺回，可在控制台输入 console 进行打印", "color:#00ffcc; font-weight:bold;");
    } catch (e) {}

    // ==========================================
    // 2. 注入无黑边 CSS
    // ==========================================
    const injectCSS = () => {
        const style = document.createElement('style');
        style.id = 'kirka-cn-font-style';
        style.textContent = `
            #app, #app *, #app div, #app span, #app button, #app p, #app a {
                font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif !important;
                -webkit-font-smoothing: antialiased !important;
                -moz-osx-font-smoothing: grayscale !important;
                font-style: normal !important;
                text-transform: none !important;
                text-shadow: none !important;
                -webkit-text-stroke: 0px transparent !important;
                text-decoration: none !important;
            }
            #kirka-cn-panel, #kirka-cn-panel * {
                font-size: 14px !important;
                font-family: monospace !important;
                line-height: normal !important;
                text-shadow: none !important;
            }
        `;
        (document.head || document.documentElement).appendChild(style);
    };
    injectCSS();

    // ==========================================
    // 3. 基础词典 (可运行时增删)
    // ==========================================
    const exactDict = {
        // --- 基础 UI 与 稀有度 ---
        "HUB": "大厅", "STORE": "商店", "SERVERS": "服务器", "QUESTS": "任务", "FRIENDS": "好友",
        "CLANS": "战队", "INVENTORY": "库存", "MARKET": "市场", "EDITOR": "地图编辑器", "SETTINGS": "设置",
        "PLAY": "开始游戏", "PLAY SETTINGS": "游戏设置", "PRIVATE": "私人房间", "JOIN": "加入",
        "USER EXPERIMENTS": "用户实验", "ADD PARTY": "添加队伍", "ADD FRIEND": "添加好友",
        "DAILY QUESTS": "每日任务", "EVENT QUESTS": "活动任务", "DAILY STREAK": "每日连击", "DAILY-STREAK": "每日连击",
        "HOURLY": "每小时", "DAY": "天", "LIVE STREAMS": "直播", "TOP PLAYERS": "顶尖玩家", "KIRKA NEWS": "KIRKA 新闻",
        "LOADING": "加载中", "LOADING...": "加载中...", "Loading...": "加载中...", "SEARCHING GAME": "搜索游戏中",
        "GAME FOUND": "已找到游戏", "READY": "准备", "not ready": "未准备", "LEAVE THE MATCH": "离开比赛",
        "LOGIN TO SAVE PROGRESS": "登录以保存进度", "CLIENT DOWNLOAD": "下载客户端", "DOWNLOAD": "下载",
        "NEWS": "新闻", "MENU": "菜单", "See more...": "查看更多...", "Login or Register": "登录或注册",
        "Link account": "关联账号", "Matchmaking": "匹配", "Newbie": "新手", "INVITE": "邀请", "REQUEST": "请求",
        "Info": "信息", "Type": "类型", "Default": "默认", "CLIENT": "客户端", "Time": "时间",
        "dev": "开发者", "Unselect All": "取消全选", "Failed to get market": "获取市场失败", "COPY TO CLIPBOARD": "复制到剪贴板",
        "Coins: No": "金币: 否", "Damage: Yes": "伤害: 是", "XP: No": "经验: 否", "All": "全部", "Find": "查找",
        "YOUR ID:": "你的 ID：", "lvl": "等级", "CHESTS": "宝箱", "COPIED 🔖": "已复制 🔖",
        "Minutes left": "剩余分钟", "Yes": "是", "No": "否", "Connect": "连接", "CHANGE": "更改",
        "CONTINUE": "继续", "ENTER": "进入", "EXIT": "退出", "TRADE": "交易", "back": "返回", "HP": "生命值",

        // --- 第三方登录 ---
        "LOGIN WITH APPLE": "使用 Apple 登录",
        "LOGIN WITH DISCORD": "使用 Discord 登录",
        "LOGIN WITH FACEBOOK": "使用 Facebook 登录",
        "LOGIN WITH GOOGLE": "使用 Google 登录",
        "LOGIN WITH TWITCH": "使用 Twitch 登录",
        "LOGIN WITH VK": "使用 VK 登录",
        "LOGIN WITH YOUTUBE": "使用 YouTube 登录",

        // --- 计分板与游戏内状态 ---
        "BLUE TEAM": "蓝队", "RED TEAM": "红队", "ASSIST": "助攻", "KILL": "击杀",
        "MELEE": "近战", "MID-AIR": "空中", "SPECTATE": "观战", "damage taken": "承受伤害",
        "death": "死亡", "friend": "好友", "kills": "击杀", "report": "举报", "score": "得分", "cRouch": "蹲下",

        // --- 特定名称 ---
        "LOLKin 与乌鸦": "LOLKin 与乌鸦", "LOLKin and Crow": "LOLKin 与乌鸦",

        // --- 服务器区域 ---
        "ASIA": "亚洲", "EU": "欧洲", "NA": "北美", "OCEANIA": "大洋洲", "SA": "南美", "INDIA": "印度",
        "Asia": "亚洲", "Europe": "欧洲", "India": "印度", "North America": "北美", "Oceania": "大洋洲", "South America": "南美",

        // --- 社交与 Twitch ---
        "Connect your Twitch account to enable Twitch drops": "连接你的 Twitch 账号以启用 Twitch 掉落",
        "Twitch": "Twitch", "Auto-decline all clan invitations": "自动拒绝所有战队邀请",
        "Automatically ignore clan invites": "自动忽略战队邀请", "Clans": "战队",
        "Trade accept": "接受交易", "Trade decline": "拒绝交易", "Trade offer": "交易报价",

        // --- 等级与奖励限制 ---
        "LEVELS": "等级", "No reward": "无奖励", "Party": "队伍", "Wood": "木头",
        "experience to the next level": "距离下一级所需经验",
        "Quantum": "量子", "Sorcery": "魔法", "Synth": "合成",
        "REACH LVL 10 TO CREATE A CLAN": "达到 10 级以创建战队",

        // --- 高级画质与特效设置 ---
        "AO": "环境光遮蔽", "Ambient occlusion (disable for performance)": "环境光遮蔽 (关闭以提升性能)",
        "Brightness of the map": "地图亮度", "Brightness of the map ambient occlusion": "地图环境光遮蔽亮度",
        "Contrast of the map directional lighting": "地图方向光对比度", "Lower for performance": "降低以提升性能",
        "Render shadows. Disable for performance.": "渲染阴影。关闭以提升性能。",
        "Shadow map resolution. Lower for performance.": "阴影贴图分辨率。降低以提升性能。",
        "Use square images (eg: 512x512)": "使用正方形图片 (例如: 512x512)",
        "Default scope, custom image, or custom crosshair": "默认瞄准镜、自定义图片或自定义准星",
        "How to add an image": "如何添加图片", "Knife roll animation speed (0 = disabled)": "匕首滚动动画速度 (0 = 禁用)",
        "Scale of damage numbers": "伤害数字缩放", "Show directional damage indicator": "显示方向伤害指示器",
        "Show floating damage numbers": "显示浮动伤害数字", "RGB animation (disable for performance)": "RGB 动画 (关闭以提升性能)",
        "Block animations": "方块动画", "Block animations (disable for performance)": "方块动画 (关闭以提升性能)",
        "Map texture (disable for performance)": "地图纹理 (关闭以提升性能)",
        "Play players animations (disable for performance)": "播放玩家动画 (关闭以提升性能)",
        "Show bullet holes (disable for performance)": "显示弹孔 (关闭以提升性能)",
        "Show bullets (disable for performance)": "显示子弹 (关闭以提升性能)",
        "Show players HP bar (disable for performance)": "显示玩家生命值条 (关闭以提升性能)",
        "Show players texture (disable for performance)": "显示玩家纹理 (关闭以提升性能)",
        "Show players weapon (disable for performance)": "显示玩家武器 (关闭以提升性能)",
        "Skybox textures (disable for performance)": "天空盒纹理 (关闭以提升性能)",
        "Players highlight color": "玩家高亮颜色",
        "Pull Y": "拉动 Y", "Pull Y Speed": "拉动 Y 速度", "Pull Y Speed Reverse": "拉动 Y 速度反转",
        "Pull Z": "拉动 Z", "Pull Z Speed": "拉动 Z 速度", "Pull Z Speed Reverse": "拉动 Z 速度反转",
        "Arms Animation": "手臂动画", "Custom Texture": "自定义贴图", "Texture": "纹理", "Image": "图片",
        "RGB": "RGB", "skybox": "天空盒", "map": "地图", "Players": "玩家",

        // --- 核心设置菜单 ---
        "GENERAL": "通用", "GRAPHICS": "图形", "CONTROLS": "控制", "SOUNDS": "声音", "general": "通用", "graphics": "图形", "controls": "控制", "sounds": "声音",
        "Sounds": "声音", "Chat": "聊天", "Camera": "视角", "Performance": "性能",
        "Keybindings": "按键绑定", "mods": "模组", "Menu": "菜单",
        "Aim down sight strength": "瞄准(ADS)强度", "FPS (Spectating)": "帧率 (观战中)", "TPS (Spectating)": "TPS (观战中)",
        "Fly (Spectating)": "飞行 (观战中)", "Walls (Spectating)": "透视墙 (观战中)",
        "Next Player (Spectating)": "下一名玩家 (观战中)", "Previous Player (Spectating)": "上一名玩家 (观战中)",
        "See Scores": "查看比分", "Mode Menu (Buy)": "模式菜单 (购买)", "Predicted": "预测", "Protection": "保护",
        "Backward 2": "向后 2", "Forward 2": "向前 2", "Left 2": "向左 2", "Right 2": "向右 2",
        "Ladder Slip": "爬梯滑落", "Reduce horizontal velocity when climbing a ladder": "爬梯时减少水平速度",

        // --- 准星与动画细节 ---
        "Hitmarker fades out": "击中标记淡出", "Show a marker when you hit someone": "击中敌人时显示标记",
        "If dynamic, crosshair will react based on accuracy": "如果是动态准星，准星将根据精度做出反应",
        "The gap changes size": "间隙大小会变化", "Play the gap animation backward": "反向播放间隙动画",
        "Gap Animation": "间隙动画", "Gap Difference": "间隙差值", "Gap Reverse": "间隙反转", "Gap Speed": "间隙速度",
        "Gap animation difference": "间隙动画差值", "Gap animation speed": "间隙动画速度",
        "Fade Out Animation": "淡出动画", "Fade out animation speed": "淡出动画速度",
        "Weapons ADS": "武器瞄准(ADS)", "Scope 2": "瞄准镜 2", "Shoot 2": "射击 2", "sNiper sCope": "狙击镜",
        "Aim Sensitivity": "瞄准灵敏度", "Mouse Sensitivity": "鼠标灵敏度", "Master Volume": "主音量", "UI Volume": "界面音量",
        "Ambient Volume": "环境音量", "Action Volume": "动作音量", "Killstreak Volume": "连杀音量", "Damage Numbers": "伤害数字",
        "Damage Indicator": "伤害指示器", "Crosshair": "准星", "Center Dot": "中心点", "Color": "颜色", "Thickness": "厚度",
        "Gap": "间隙", "Outline": "轮廓", "Show": "显示", "SHOW": "显示", "Hide": "隐藏", "Hidden": "隐藏",
        "Enabled": "已启用", "FOV": "视野范围", "Weapon FOV": "武器视野", "Brightness": "亮度", "Contrast": "对比度",
        "Shadows": "阴影", "Shadow quality": "阴影质量", "Foliage": "植被", "Effects": "特效", "Physics": "物理", "PHYSICS": "物理",
        "Rendering": "渲染", "Resolution": "分辨率", "Static": "静态", "Dynamic": "动态",
        "Smooth Aim": "平滑瞄准", "Raw Input": "原始输入", "Left-handed": "左手持枪", "Mouse": "鼠标",
        "AO Brightness": "环境光遮蔽亮度", "Disable mouse acceleration": "禁用鼠标加速", "Bullets": "子弹", "Holes": "弹孔",
        "Hitmarker": "击中标记", "Opacity": "不透明度", "Size": "大小", "Scale": "比例", "Animations": "动画",
        "Arms": "手臂", "Fade Out Speed": "淡出速度", "Bottom Line": "底线", "Top Line": "顶线", "Left Line": "左线",
        "Right Line": "右线", "Flick": "甩枪", "Knife Roll Speed": "匕首滚动速度", "Stair Slide": "楼梯滑行",
        "Interact (Doors / Vending)": "交互(门/售货机)",

        // --- 武器与装备 ---
        "Equip Grenade": "装备手雷", "Equip Flash Grenade": "装备闪光弹", "Equip Frag Grenade": "装备破片手雷",
        "Equip Smoke Grenade": "装备烟雾弹", "Equip Molotov": "装备燃烧瓶", "Switch Grenade": "切换手雷",
        "WEAPONS": "武器", "SKINS": "皮肤", "CHARACTER": "角色", "CHARACTERS": "角色", "CHARACTER CARDS": "角色卡片",
        "AWARDS": "奖励", "EQUIP": "装备", "INSPECT": "检视", "Inspect": "检视", "BUY": "购买", "SALE": "促销",
        "NEW": "新", "LIMITED TIME": "限时", "COINS": "金币", "DIAMONDS": "钻石", "GOLDEN": "黄金",
        "Revolver": "左轮手枪", "SCAR": "SCAR", "Shark": "鲨鱼", "LAR": "LAR", "VITA": "VITA",
        "M60": "M60", "Tomahawk": "战斧", "Bayonet": "刺刀", "MAC10": "MAC10", "AR-9": "AR-9", "MAC-10": "MAC-10",
        "Primary Weapon": "主武器", "Secondary Weapon": "副武器", "Third Weapon": "第三武器", "Weapon": "武器",
        "Previous Weapon": "上一把武器", "Next Weapon": "下一把武器", "Reload": "重新装填", "Jump": "跳跃",
        "Crouch": "蹲下", "Dash": "冲刺", "Scroll Next Weapon": "滚轮下一把武器", "Scroll Prev Weapon": "滚轮上一把武器",
        "Forward": "向前", "Backward": "向后", "Left": "向左", "Right": "向右", "up": "上", "down": "下",
        "front": "前", "left": "左", "right": "右", "Select": "选择", "MAIN": "主界面", "GIFT": "礼物", "VIP": "VIP",
        "James": "詹姆斯", "Elizabeth": "伊丽莎白", "Weatie": "Weatie", "Rewards:": "奖励：",

        // --- 地图编辑器专属 ---
        "Block Group Manager (Editor)": "方块组管理器 (编辑器)", "Block Groups (Editor)": "方块组 (编辑器)",
        "Cancel Interact (Editor)": "取消交互 (编辑器)", "Delete Flag (Editor)": "删除旗帜 (编辑器)",
        "Delete Spawn (Editor)": "删除出生点 (编辑器)", "Delete Yellow Flag (Editor)": "删除黄旗 (编辑器)",
        "Export": "导出", "Import": "导入", "Interact (Editor)": "交互 (编辑器)",
        "Pick Block (Editor)": "选取方块 (编辑器)", "Place Sun (Editor)": "放置太阳 (编辑器)",
        "Redo (Editor)": "重做 (编辑器)", "Undo (Editor)": "撤销 (编辑器)",
        "Save Thumbnail (Editor)": "保存缩略图 (编辑器)", "Script Log (Game Owner)": "脚本日志 (房主)",
        "Set Blue Spawn (Editor)": "设置蓝队出生点 (编辑器)", "Set Flag (Editor)": "设置旗帜 (编辑器)",
        "Set Red Spawn (Editor)": "设置红队出生点 (编辑器)", "Set Yellow Flag (Editor)": "设置黄旗 (编辑器)",
        "Toggle Backpack (Editor)": "切换背包 (编辑器)", "Toggle Create Mode (Editor)": "切换建造模式 (编辑器)",
        "Toggle Flags (Editor)": "切换旗帜 (编辑器)", "Toggle Spawns (Editor)": "切换出生点 (编辑器)",
        "Toggle Yellow Flags (Editor)": "切换黄旗 (编辑器)", "Reset": "重置",

        // --- 任务/进度/好友 ---
        "Play 18 games": "游玩 18 局游戏", "Win 1 games": "赢得 1 局游戏", "kills to claim today,": "今日可领取击杀数，",
        "Common": "普通", "Epic": "史诗", "Legendary": "传说", "Rare": "稀有", "Mythical": "神话", "Hide completed": "隐藏已完成",
        "STATUS": "状态", "Online": "在线", "Away": "离开", "Busy": "忙碌", "Do not disturb": "请勿打扰",
        "No friends.": "暂无好友。", "No friends online": "暂无在线好友", "Online friends": "在线好友",
        "Send friend requests to other people!": "向其他人发送好友请求！", "Invite to Party": "邀请加入队伍",
        "Stream kirka on twitch to show up here": "在 Twitch 上直播 Kirka 即可在此展示",
        "Ask a friend to submit a request!": "让朋友提交请求！", "No requests.": "暂无请求。",

        // --- 模式/地图/描述 ---
        "1 versus 1 ranked duel": "1对1 排位对决", "Blue team against red team": "蓝队对抗红队",
        "Build maps with others": "与他人一起构建地图", "Enter and protect the flag zone": "进入并保护旗帜区域",
        "Low gravity and faster speed": "低重力与更快的速度", "Only melee weapons allowed": "仅允许近战武器",
        "Search and destroy the gem": "搜索并摧毁宝石", "Reach the end within the best time": "在最佳时间内到达终点",
        "Trade items with other players": "与其他玩家交易物品",
        "MOST PLAYED": "最常游玩", "NEWEST": "最新发布", "USER-EXPERIMENTS": "用户实验",
        "1V1 TAG FIGHTCLUB": "1V1 标签格斗俱乐部", "1V1 TAG RURAL": "1V1 标签乡村",
        "Akuma": "阿库玛", "Black Mass": "黑弥撒", "Blacklung Basin": "黑肺盆地", "Bridge Parkour": "桥梁跑酷",
        "Bridge Rush": "桥梁冲锋", "Bunker Incident": "地堡事件", "Corrupt": "腐化", "Downfall": "陨落",
        "Gem League": "宝石联赛", "Geometric (TRADE)": "几何 (交易)", "Gun Game: Wanted": "枪战游戏：通缉",
        "Gunners VS Runners (Bo0fi)": "枪手 VS 跑者 (Bo0fi)", "Hide_and_Seek": "捉迷藏",
        "Hollow Halls (Zombies)": "空洞走廊 (僵尸)", "Juggernaut": "主宰", "Morning": "早晨",
        "Murder Mystery": "谋杀之谜", "MURDER MYSTERY": "谋杀之谜", "Overgrown Castle": "杂草丛生的城堡",
        "Ping! Classic Game of Pong": "乒乓！经典乒乓球游戏", "Point DM": "占点死斗", "Pong": "乒乓",
        "RITE Aim Lab": "RITE 瞄准实验室", "RITE La Cripta": "RITE 地穴", "RITE Last to Fall": "RITE 坚持到底",
        "RITE: Final Break": "RITE: 最终突破", "RITE: Halloween Fair": "RITE: 万圣节游园会",
        "RITE: Meltdown (Zombies Quest)": "RITE: 熔毁 (僵尸任务)", "Rev Spleef": "反向破坏方块",
        "Rush": "冲锋", "Search and Destroy Economy": "搜索与摧毁 经济模式", "Survival Horror": "生存恐怖",
        "The Killers": "杀手", "Tower Arena": "塔楼竞技场", "Trenches (Gun Game)": "战壕 (枪战游戏)",
        "WEAPONRY": "武器库", "Weapon Concepts": "武器概念", "ZOMBIES: DEAD ZONE": "僵尸：死亡地带",
        "scarey hotel": "恐怖酒店", "CTF + Grenades": "夺旗 + 手雷",
        "CTF with grenades, to test the experiments": "带手雷的夺旗模式，用于测试实验功能",
        "Inspired by Quake LG Duels": "灵感来自 Quake LG 对决", "Jump and dont die:)": "跳跃但别死:)",
        "Play 1v1 or 2v2 Football/Soccer": "游玩 1v1 或 2v2 足球赛",
        "Shark is Grapple, Weatie Rocket, etc...": "鲨鱼是抓钩，Weatie 是火箭筒，等等...",
        "zombie mode fixed(made with pseudoical)": "僵尸模式修复版(由 pseudoical 制作)",

        // --- 地图名 ---
        "Ancient": "远古", "Apartment": "公寓", "Arid": "干旱", "Backrooms": "后室", "Bed": "床铺",
        "BootyBay": "藏宝海湾", "Castle": "城堡", "Catacomb": "地下墓穴", "Cathedral": "大教堂", "Cave": "洞穴",
        "Co2 XL": "Co2 XL", "Culvert": "涵洞", "Desty": "Desty", "Dreams": "梦境", "Eruption": "火山爆发",
        "Grass": "草地", "Gulag": "古拉格", "Highrises": "高楼", "Hydraulic": "液压", "Islands": "岛屿",
        "Kitchen": "厨房", "Lava": "熔岩", "Lockup": "禁闭室", "Mefitis": "Mefitis", "Moss": "苔藓",
        "Obstruction": "障碍", "Palace": "宫殿", "Pool": "泳池", "Prison": "监狱", "Race": "竞速",
        "Sandstorm": "沙尘暴", "Shipment": "货轮", "Ski": "滑雪", "Skyhigh": "摩天", "Skytown": "天空之城",
        "Story": "故事", "SunkenTemple": "沉没神庙", "Tectonic": "地壳", "Tenebris": "Tenebris", "Terra": "Terra",
        "Toilet": "厕所", "Tower": "塔楼", "Train": "列车", "Tunnel": "隧道", "Umbral": "暗影", "Underwater": "水下",
        "Warehouse": "仓库", "Windmill": "风车", "Zenith": "天顶", "Acid": "酸性", "Blossom": "花开", "Bulwark": "堡垒",
        "Clash": "冲突", "Cold": "寒冷", "Colyseum": "竞技场", "Digsite": "挖掘场", "Dust": "沙尘", "Fortress": "堡垒",
        "Frontier": "边境", "Funeral": "葬礼", "Inferno": "地狱", "Lost": "迷失", "Minimart": "小卖部",
        "Mirage": "海市蜃楼", "Nebu": "Nebu", "North": "北方", "Nuke": "核弹", "Nuketown": "核弹镇",
        "Parallax": "视差", "Poussiere": "灰尘", "Rialto": "里亚托", "Sanctuary": "避难所", "Sealed": "封锁",
        "Siege": "围攻", "Storage": "仓库", "Sundial": "日晷", "Terminal": "终端", "Towers": "双塔",
        "Town": "小镇", "Verdant": "翠绿", "Vertigo": "眩晕", "Village": "村庄", "Railyard": "铁路调车场",
        "Temple": "神庙", "temple": "神庙", "Ceres": "Ceres", "Antfarm": "蚁农场", "Bedroom": "卧室", "Cleft": "裂缝",
        "Collision": "碰撞", "Dethroned": "废黜", "Derelict": "废弃", "Diablo": "暗黑", "Dune": "沙丘",
        "Favela": "贫民窟", "Gym": "体育馆", "Hallway": "走廊", "Juxt": "Juxt", "Labs": "实验室",
        "Long Shot": "远射", "Lotus": "莲花", "Metro": "地铁", "Royale": "皇家", "Ruins": "废墟",
        "Rust": "铁锈", "Schism": "分裂", "Shore": "海岸", "Slate": "石板", "Snowfort": "雪堡",
        "Street": "街道", "Summer": "夏日", "TKO": "TKO", "BEAM DUELS": "光束对决", "Beam Duels": "光束对决",
        "RED LIGHT - GREEN LIGHT": "红灯 - 绿灯", "GRASS": "草地", "SK8": "SK8", "Bathroom": "浴室", "Kharid": "Kharid",

        // --- 模式/规则 ---
        "DM": "死斗", "TDM": "团队死斗", "POINT": "占点", "POINT 2V2": "占点 2V2", "PARKOUR": "跑酷",
        "SEARCH AND DESTROY": "搜索与摧毁", "KNIFE ONLY": "仅限匕首", "LAR ONLY": "仅限LAR", "LAR only": "仅限LAR",
        "RANKED": "排位", "Warmup only": "仅限热身", "CUSTOM": "自定义", "MAP": "地图", "MODE": "模式",
        "PLAYERS": "玩家", "ALL": "全部", "SELECT MAPS": "选择地图", "SELECT MODES": "选择模式",
        "BLUE": "蓝队", "Checkpoint": "检查点", "Free for all": "自由混战", "Event": "活动", "Experimental": "实验性",
        "New Mode: Knife only": "新模式：仅限匕首", "New mode: Parkour": "新模式：跑酷", "Sabotage mode": "破坏模式",
        "Zombies mode": "僵尸模式", "CLAN WAR": "战队战", "TRADE mode": "交易模式", "USER MODE": "用户模式",
        "Knife only": "仅限匕首", "Parkour": "跑酷", "Physics": "物理", "Zombies": "僵尸", "Sabotage": "破坏",

        // ==========================================
        // 新增：昵称 / 改名提示
        // ==========================================
        "CHANGE NICKNAME": "更改昵称", "Change": "更改",

        // ==========================================
        // 新增：开箱 / 宝箱 / 通用按钮 / 错误提示
        // ==========================================
        "YOUR CHESTS": "你的宝箱", "Chest Odds": "宝箱概率", "TOP PULLS": "最高抽取",
        "AUTO-OPEN": "自动开启", "OPEN 10": "开启 10 个", "OPEN": "开启", "CLOSE": "关闭",
        "SELL": "出售", "SERVER": "服务器", "LIVE FEED": "实时画面", "OK": "确定",
        "CONNECTION LOST": "连接已断开", "AFK": "挂机",
        "You were kicked from the room due to been inactive": "你因长时间未操作被移出房间",
        "Unexpectedly disconnected from lobby while entering room": "进入房间时意外从大厅断开连接",
        "killed you with their": "被对方的武器击杀",
        "DASH": "冲刺", "SHIFT": "Shift", "TAB": "Tab", "Normal Map": "法线贴图",
        "2025 Revolver": "2025 左轮手枪", "kIllbar": "击杀条",
        "Try": "尝试", "Height": "高度",

        // ==========================================
        // 新增：皮肤 / 饰品名
        // ==========================================
        "Antique": "古董", "Artic Illusion": "极光幻象", "Awesome": "惊艳", "Aztek": "阿兹特克",
        "Bee": "蜜蜂", "Black Metal": "黑金属", "Blackout": "全黑", "Blood Crystal": "血水晶",
        "Blue Hell": "蓝色地狱", "Blueberry": "蓝莓", "Bubblegum": "泡泡糖", "Candy Illusion": "糖果幻象",
        "Capricorn": "摩羯座", "Carbon Fade": "碳纤维渐变", "Cargo": "货箱", "Case Hardened": "表面淬火",
        "Checker": "棋盘格", "Chess": "国际象棋", "Complexity": "复杂度", "Cornfield": "玉米田",
        "Cosmos": "宇宙", "Crash": "崩溃", "Cult": "邪教", "Cyan": "青色", "Cyber": "赛博",
        "Cyberpunk": "赛博朋克", "DILLPICKLE": "酸黄瓜", "Damascus": "大马士革", "Darling": "亲爱的",
        "Demon": "恶魔", "Donut": "甜甜圈", "Drake": "德雷克", "Engravement": "雕刻",
        "Fade": "渐变", "Fading Waves": "消退之浪", "Fire": "火焰", "Flow": "流动", "Forest": "森林",
        "Fun": "趣味", "Fur": "毛皮", "Galaxy": "银河", "Gem": "宝石", "Ghost": "幽灵",
        "Glacial": "冰川", "Gloop": "黏液", "Golden": "黄金", "Hardened": "淬火", "Heart": "爱心",
        "Heatwave": "热浪", "Hello": "你好", "Hexagon": "六边形", "Hologram": "全息",
        "Honey": "蜂蜜", "Hope": "希望", "Infernal": "地狱火", "Infra": "红外", "Isolation": "隔离",
        "Ivoire": "象牙", "Jade": "翡翠", "Lantern": "灯笼", "Lemon": "柠檬", "Leopard": "豹纹",
        "Lux": "光耀", "Magic Splat": "魔法泼溅", "Magnum": "马格南", "Majestic": "威严",
        "Malachite": "孔雀石", "Metallic": "金属", "Metallic Rainbow": "金属彩虹", "Mohito": "莫吉托",
        "Molten Core": "熔核", "Monkey": "猴子", "Murdered": "谋杀", "Mystic": "神秘", "Nebula": "星云",
        "Neon": "霓虹", "Nuclear Waste": "核废料", "Obsidian": "黑曜石", "Peachy": "桃色",
        "Pineapple": "菠萝", "Pink Camouflage": "粉色迷彩", "Pink Demon": "粉色恶魔", "Plum": "李子",
        "Psychedelic": "迷幻", "Psycho": "疯狂", "Pulse": "脉冲", "Pumpknight": "南瓜骑士",
        "Pumpsnipe": "南瓜狙击", "Rainbow": "彩虹", "Rasta": "拉斯塔", "Redline": "红线",
        "Reptile": "爬行动物", "Retro": "复古", "Sakura": "樱花", "Santa": "圣诞老人",
        "Scary": "恐怖", "Shiny": "闪亮", "Simplicity": "简约", "Sleep": "睡眠",
        "Spectacular": "壮丽", "Spotted": "斑点", "Strips": "条纹", "Teflon": "特氟龙",
        "Terminator": "终结者", "Toy": "玩具", "Tricky": "诡计", "Trolled": "被耍",
        "Universe": "宇宙", "Viking": "维京", "Vivid": "鲜艳", "Volcano": "火山",
        "Wacky": "古怪", "Whiteout": "白茫茫", "Winter": "冬天", "Zebra": "斑马"
    };

    // 动态词典与正则
    const actionDict = {
        "Added": "添加了", "Updated": "更新了", "Removed": "移除了", "Fixed": "修复了",
        "Re-added": "重新添加了", "Readded": "重新添加了", "Raised": "提高了", "Reduced": "降低了",
        "Lowered": "降低了", "Moved": "移动了", "Replaced": "替换了", "Renamed": "重命名了"
    };

    const regexDict = [
        { regex: /^Expire in ([\d:]+)$/i, replace: "$1 后过期" },
        { regex: /^Reset in (.+)$/i, replace: "$1 后重置" },
        { regex: /^([\d\s,]+) xp$/i, replace: "$1 经验" },
        { regex: /^([\d\/]+) UNITS LEFT$/i, replace: "剩余 $1 个单位" },
        { regex: /^(\d+) selected$/i, replace: "已选择 $1" },
        { regex: /^(\d+) item found$/i, replace: "找到 $1 个物品" },
        { regex: /^(\d+) days left$/i, replace: "剩余 $1 天" },
        { regex: /^You need level (\d+) to use the market$/i, replace: "你需要达到 $1 级才能使用市场" },
        { regex: /^Level (\d+) required$/i, replace: "需要等级 $1" },
        { regex: /^(.+) joined the game$/i, replace: "$1 加入了游戏" },
        { regex: /^(.+) left the game$/i, replace: "$1 离开了游戏" },
        { regex: /^killed you with their (.+)$/i, replace: "被他们的 $1 击杀" },
        { regex: /^(.+) killed you with their (.+)$/i, replace: "$1 用他们的 $2 击杀了你" },
        { regex: /^coins x(\d+)$/i, replace: "金币 x$1" },
        { regex: /^diamonds x(\d+)$/i, replace: "钻石 x$1" },
        { regex: /^(\d+) x (.+)$/i, replace: "$1 个 $2" },
        { regex: /^(.+) KD$/i, replace: "$1 KD" },
        { regex: /^Kills ([\d]+)\/([\d]+)$/i, replace: "击杀 $1/$2" },
        { regex: /^(\d+) online$/i, replace: "$1 人在线" },
        { regex: /^COMMENTS \((\d+)\)$/i, replace: "评论 ($1)" },
        { regex: /^Map by (.+) and Mode by (.+)$/i, replace: "地图作者 $1，模式作者 $2" },
        { regex: /^Earn ([\d,]+) score with (.+)$/i, replace: "使用 $2 获得 $1 分数" },
        { regex: /^Earn ([\d,]+) score in a single game$/i, replace: "单场游戏获得 $1 分数" },
        { regex: /^Get ([\d,]+) headshots with (.+)$/i, replace: "使用 $2 获得 $1 爆头" },
        { regex: /^Get ([\d,]+) kills with (.+)$/i, replace: "使用 $2 获得 $1 击杀" },
        { regex: /^Get ([\d,]+) headshots in a single game$/i, replace: "单场游戏获得 $1 爆头" },
        { regex: /^Get ([\d,]+) kills in a single game$/i, replace: "单场游戏获得 $1 击杀" },
        { regex: /^Get ([\d,]+) kills$/i, replace: "获得 $1 击杀" },
        { regex: /^Get a ([\d,]+) killstreak$/i, replace: "获得 $1 连杀" },
        { regex: /^Get one of (\d+) skins$/i, replace: "获得 $1 个皮肤之一" },
        { regex: /^Get (\d+) headshots$/i, replace: "获得 $1 爆头" },
        { regex: /^(\d+) minute left$/i, replace: "剩余 $1 分钟" },
        { regex: /^(\d+) minutes left$/i, replace: "剩余 $1 分钟" },
        { regex: /^(\d+) viewers$/i, replace: "$1 名观众" },
        { regex: /^(\d+) subscribers$/i, replace: "$1 名订阅者" },
        { regex: /^Added ([\d]+0) degrees Bonus$/i, replace: "添加 $1 度加成" },
        { regex: /^Added ([\d]+) store$/i, replace: "添加 $1 商店" },
        { regex: /^Added ([\d]+) revolver skins$/i, replace: "添加 $1 左轮手枪皮肤" },
        { regex: /^Added ([\d]+) Mythical skins$/i, replace: "添加 $1 神话皮肤" },
        { regex: /^Added ([\d]+) new weapon skins$/i, replace: "添加 $1 个新武器皮肤" },
        { regex: /^(\d+)h (\d+)min (\d+)s$/i, replace: "$1小时 $2分 $3秒" },
        { regex: /^v([\d\.]+) - (January|February|March|April|May|June|July|August|September|October|November|December) (\d+), (\d+)$/i,
          replace: function(match, version, monthStr, day, year) {
              const months = { "January":"1月", "February":"2月", "March":"3月", "April":"4月", "May":"5月", "June":"6月", "July":"7月", "August":"8月", "September":"9月", "October":"10月", "November":"11月", "December":"12月" };
              return `v${version} - ${year}年${months[monthStr]}${day}日`;
          }
        },

        // ==========================================
        // 新增动态规则
        // ==========================================
        { regex: /^Hi, (.+?)\. You have the option to change your name\.?$/i, replace: "你好，$1。你可以选择更改你的名字。" },
        { regex: /^(\d+)\/(\d+) left$/i, replace: "剩余 $1/$2" },
        { regex: /^Try to reconnect for (\d+)s\.\.\.$/i, replace: "尝试重新连接，剩余 $1 秒..." },
        { regex: /^(.+?) x(\d+)$/i,
          replace: function (m, name, n) {
              var zh = exactDict[name] || exactDict[name.charAt(0).toUpperCase() + name.slice(1)] || name;
              return zh + " ×" + n;
          }
        }
    ];

    // ==========================================
    // 4. 智能动态解析器
    // ==========================================
    function processDynamicLog(str) {
        const match = str.match(/^(Added|Updated|Removed|Fixed|Re-added|Readded|Raised|Reduced|Lowered|Moved|Replaced) (.+?)( map)?( \(experimental\))?$/i);
        if (!match) return null;

        const action = match[1];
        let rest = match[2];
        const isExp = !!match[4];
        let actionCN = actionDict[action] || actionDict[action.charAt(0).toUpperCase() + action.slice(1).toLowerCase()] || action;

        let isMap = false;
        if (match[3]) { isMap = true; rest = rest.trim(); }

        let restCN = exactDict[rest] || exactDict[rest.charAt(0).toUpperCase() + rest.slice(1)] || rest;
        let result = `${actionCN} ${restCN}`;
        if (isMap && !restCN.includes("地图")) result += " 地图";
        if (isExp) result += " (实验性)";
        return result;
    }

    // ==========================================
    // 5. 核心翻译与收集引擎
    // ==========================================
    const untranslatedSet = new Set();
    let isCollectorVisible = GM_getValue("kirka_collector_visible", true); // 默认开启
    let btnElement = null;

    function updatePanel() {
        if (!isCollectorVisible) {
            if (btnElement) btnElement.style.display = 'none';
            return;
        }
        if (!btnElement) {
            btnElement = document.createElement('div');
            btnElement.id = 'kirka-cn-panel';
            btnElement.style.cssText = `
                position: fixed; bottom: 20px; right: 20px; background: rgba(0, 0, 0, 0.8);
                color: #ffcc00; border: 1px solid #ffcc00; padding: 8px 12px; border-radius: 6px;
                font-family: monospace; font-size: 14px; z-index: 999999; cursor: pointer;
                box-shadow: 0 4px 10px rgba(0,0,0,0.5); user-select: none; pointer-events: auto;
                transition: opacity 0.3s;
            `;
            btnElement.onclick = () => {
                if (untranslatedSet.size === 0) {
                    alert("暂时没有未翻译的字段！");
                    return;
                }
                const text = [...untranslatedSet].sort().join('\n');
                navigator.clipboard.writeText(text).then(() => {
                    alert(`✅ 成功复制了 ${untranslatedSet.size} 个未翻译字段到剪贴板！`);
                }).catch(() => {
                    alert("复制失败，请打开控制台查看。");
                });
            };
            document.body.appendChild(btnElement);
        }
        btnElement.style.display = 'block';
        btnElement.innerHTML = `📝 未翻译词: ${untranslatedSet.size} (点击复制)`;
    }

    function recordUntranslated(text) {
        if (!text || text.length < 2 || text.length > 60) return;
        if (untranslatedSet.has(text)) return;
        if (text.includes('http') || text.includes('.io')) return;
        if (text.split(' ').length > 8) return;
        if (/^[A-Za-z0-9#_\-]+$/.test(text) && /\d/.test(text) && text.length < 15) return;
        if (/^[\-|\s]+/.test(text)) return;

        untranslatedSet.add(text);
        updatePanel();
    }

    function getTranslation(str) {
        if (!str || typeof str !== 'string' || !str.trim()) return str;
        if (!/[a-zA-Z]/.test(str)) return str;

        const t = str.trim();
        let replaced = null;

        if (exactDict[t]) {
            replaced = exactDict[t];
        } else {
            replaced = processDynamicLog(t);
        }

        if (!replaced) {
            for (const item of regexDict) {
                if (item.regex.test(t)) {
                    replaced = t.replace(item.regex, item.replace);
                    break;
                }
            }
        }

        if (replaced && replaced !== t) {
            const prefix = str.match(/^\s*/)[0];
            const suffix = str.match(/\s*$/)[0];
            return prefix + replaced + suffix;
        } else {
            recordUntranslated(t);
            return str;
        }
    }

    // ==========================================
    // 6. 底层 Hook 大阵
    // ==========================================
    const hookProperty = (obj, prop, isNodeTextOnly = false) => {
        const desc = Object.getOwnPropertyDescriptor(obj, prop);
        if (desc && desc.set) {
            Object.defineProperty(obj, prop, {
                get: desc.get,
                set: function (val) {
                    if ((!isNodeTextOnly || this.nodeType === 3) && typeof val === 'string') {
                        return desc.set.call(this, getTranslation(val));
                    }
                    return desc.set.call(this, val);
                },
                configurable: true,
                enumerable: desc.enumerable
            });
        }
    };

    hookProperty(Node.prototype, 'nodeValue', true);
    if (window.CharacterData) hookProperty(CharacterData.prototype, 'data', true);
    hookProperty(Node.prototype, 'textContent', false);
    if (window.HTMLElement) hookProperty(HTMLElement.prototype, 'innerText', false);

    const origCreateTextNode = document.createTextNode;
    document.createTextNode = function (text) {
        return origCreateTextNode.call(document, getTranslation(text));
    };

    // 初始扫描
    const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'INPUT', 'CODE', 'PRE', 'CANVAS', 'IMG']);
    function walkInitial(node) {
        if (!node) return;
        if (node.nodeType === 3) {
            const original = node.nodeValue;
            const translated = getTranslation(original);
            if (translated !== original) {
                const desc = Object.getOwnPropertyDescriptor(Node.prototype, 'nodeValue');
                desc.set.call(node, translated);
            }
        } else if (node.nodeType === 1 && !SKIP_TAGS.has(node.tagName)) {
            const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, null, false);
            let child;
            while (child = walker.nextNode()) walkInitial(child);
        }
    }

    window.addEventListener('DOMContentLoaded', () => {
        walkInitial(document.getElementById('app') || document.body);
        setTimeout(() => { walkInitial(document.getElementById('app') || document.body); updatePanel(); }, 1000);
    });

    // ==========================================
    // 7. 注册油猴菜单
    // ==========================================
    GM_registerMenuCommand("开关：未翻译词收集器", () => {
        isCollectorVisible = !isCollectorVisible;
        GM_setValue("kirka_collector_visible", isCollectorVisible);
        updatePanel();
        // 提示用户
        alert(isCollectorVisible ? "未翻译收集器：已开启" : "未翻译收集器：已关闭");
    });
})();