#!/bin/bash
# CLL 项目从源码构建部署脚本

set -e

echo "=========================================="
echo "  CLL 项目 Docker 构建部署脚本"
echo "=========================================="

# 配置
IMAGE_NAME="sehuatang-crawler"
IMAGE_TAG="latest"
CONTAINER_NAME="sehuatang-app"
DB_CONTAINER="sehuatang-postgres"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装"
    exit 1
fi

echo "✅ Docker 环境检查通过"

# 创建目录
echo ""
echo "📁 创建必要目录..."
mkdir -p data logs

# 克隆项目（如果不存在）
if [ ! -d "cll" ]; then
    echo ""
    echo "📥 克隆项目..."
    git clone https://github.com/blank-cat-1/cll.git
fi

cd cll

# 应用修复文件（如果存在）
echo ""
echo "🔧 检查修复文件..."
if [ -f "../collect_cookies.py" ]; then
    echo "   应用 collect_cookies.py 修复..."
    cp ../collect_cookies.py ./
fi

if [ -f "../domain_detector.py" ]; then
    echo "   应用 domain_detector.py..."
    cp ../domain_detector.py ./
fi

# 构建镜像
echo ""
echo "🔨 构建 Docker 镜像（这可能需要几分钟）..."
docker build -f Dockerfile.prod -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo ""
echo "✅ 镜像构建完成"

# 创建 docker-compose.yml
echo ""
echo "📝 创建 docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  sehuatang-app:
    image: sehuatang-crawler:latest
    container_name: sehuatang-app
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DATABASE_HOST=postgres
      - DATABASE_PORT=5432
      - DATABASE_NAME=sehuatang_db
      - DATABASE_USER=postgres
      - DATABASE_PASSWORD=sehuatang123
      - APP_HOST=0.0.0.0
      - APP_PORT=8000
      - APP_RELOAD=false
      - DEBUG=false
      # 代理配置（如需要请取消注释并修改）
      # - HTTP_PROXY=http://your-proxy:port
      # - HTTPS_PROXY=http://your-proxy:port
      # Cookie 相关配置
      - HEADLESS=true
      - MAX_CF_WAIT=120
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
    networks:
      - cll-network

  postgres:
    image: postgres:15-alpine
    container_name: sehuatang-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=sehuatang_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=sehuatang123
      - POSTGRES_INITDB_ARGS=--encoding=UTF8 --lc-collate=C --lc-ctype=C
      - LANG=C.UTF-8
      - LC_ALL=C.UTF-8
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - cll-network

networks:
  cll-network:
    driver: bridge

volumes:
  postgres_data:
EOF

# 停止旧容器
echo ""
echo "🛑 停止旧容器..."
docker-compose down 2>/dev/null || true

# 启动服务
echo ""
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo ""
echo "⏳ 等待服务启动..."
sleep 10

# 检查状态
echo ""
echo "📊 服务状态:"
docker-compose ps

# 显示日志
echo ""
echo "📋 最近日志:"
docker-compose logs --tail=20

echo ""
echo "=========================================="
echo "  ✅ 部署完成！"
echo "=========================================="
echo ""
echo "🌐 访问地址: http://localhost:8000"
echo "🔑 默认密码: admin123"
echo ""
echo "📝 常用命令:"
echo "   查看日志: docker-compose logs -f"
echo "   重启服务: docker-compose restart"
echo "   停止服务: docker-compose down"
echo ""
