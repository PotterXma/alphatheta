/**
 * AlphaTheta Scanner Daemon — PM2 部署配置
 *
 * 安装: npm install -g pm2
 * 启动: pm2 start ecosystem.config.js
 * 查看: pm2 logs scanner
 * 重启: pm2 restart scanner
 */
module.exports = {
    apps: [
        {
            name: "scanner",
            script: "scanner_entry.py",
            interpreter: "python3",
            cwd: "./backend",
            max_memory_restart: "256M",
            autorestart: true,
            watch: false,
            env: {
                PYTHONUNBUFFERED: "1",
                SCAN_INTERVAL_SECONDS: "900",
            },
            // 日志轮转
            log_date_format: "YYYY-MM-DD HH:mm:ss",
            error_file: "./logs/scanner-error.log",
            out_file: "./logs/scanner-out.log",
            merge_logs: true,
            max_size: "10M",
            retain: 5,
        },
    ],
};
