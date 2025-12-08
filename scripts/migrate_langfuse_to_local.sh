#!/bin/bash
# 数据迁移脚本：从langfuse-postgres-1迁移到独立PostgreSQL容器
# 版本: 1.0
# 日期: 2025-12-08

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
SOURCE_CONTAINER="langfuse-postgres-1"
SOURCE_DB="intent_test"
SOURCE_USER="postgres"
TARGET_CONTAINER="intent-test-db-prod"
TARGET_DB="intent_test"
TARGET_USER="intent_user"
BACKUP_DIR="./database_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="${BACKUP_DIR}/langfuse_migration_${TIMESTAMP}.sql"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}数据库迁移工具${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# 步骤1: 检查源数据库容器
echo -e "${YELLOW}[1/7] 检查源数据库容器...${NC}"
if ! docker ps --format '{{.Names}}' | grep -q "^${SOURCE_CONTAINER}$"; then
    echo -e "${YELLOW}⚠ 源容器 ${SOURCE_CONTAINER} 未运行${NC}"
    
    # 检查目标容器是否已存在且运行
    if docker ps --format '{{.Names}}' | grep -q "^${TARGET_CONTAINER}$"; then
        echo -e "${GREEN}✓ 目标容器已运行，数据库已迁移，无需重复迁移${NC}"
        exit 0
    fi
    
    echo -e "${YELLOW}提示: 如果已经迁移过，可以跳过此步骤${NC}"
    
    # 检查是否是非交互模式（CI/CD环境）
    if [ -t 0 ]; then
        # 交互模式：询问用户
        read -p "是否继续？(y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        SKIP_EXPORT=true
    else
        # 非交互模式：自动跳过
        echo -e "${YELLOW}非交互模式下自动跳过导出步骤${NC}"
        SKIP_EXPORT=true
    fi
else
    echo -e "${GREEN}✓ 源容器运行正常${NC}"
    SKIP_EXPORT=false
fi

# 步骤2: 创建备份目录
echo -e "${YELLOW}[2/7] 创建备份目录...${NC}"
mkdir -p "${BACKUP_DIR}"
echo -e "${GREEN}✓ 备份目录: ${BACKUP_DIR}${NC}"

# 步骤3: 导出数据
if [ "$SKIP_EXPORT" = false ]; then
    echo -e "${YELLOW}[3/7] 从源数据库导出数据...${NC}"
    echo "   数据库: ${SOURCE_DB}"
    echo "   导出到: ${DUMP_FILE}"
    
    docker exec -t "${SOURCE_CONTAINER}" pg_dump -U "${SOURCE_USER}" -d "${SOURCE_DB}" \
        --clean --if-exists --no-owner --no-acl > "${DUMP_FILE}"
    
    if [ $? -eq 0 ]; then
        DUMP_SIZE=$(du -h "${DUMP_FILE}" | cut -f1)
        echo -e "${GREEN}✓ 数据导出成功 (大小: ${DUMP_SIZE})${NC}"
    else
        echo -e "${RED}✗ 数据导出失败！${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}[3/7] 跳过数据导出${NC}"
    # 查找最新的备份文件
    LATEST_DUMP=$(ls -t ${BACKUP_DIR}/langfuse_migration_*.sql 2>/dev/null | head -1)
    if [ -n "$LATEST_DUMP" ]; then
        DUMP_FILE="$LATEST_DUMP"
        echo -e "${GREEN}✓ 使用现有备份: ${DUMP_FILE}${NC}"
    else
        echo -e "${RED}✗ 未找到备份文件，无法继续${NC}"
        exit 1
    fi
fi

# 步骤4: 检查目标容器
echo -e "${YELLOW}[4/7] 检查目标数据库容器...${NC}"
if ! docker ps --format '{{.Names}}' | grep -q "^${TARGET_CONTAINER}$"; then
    echo -e "${RED}✗ 目标容器 ${TARGET_CONTAINER} 未运行！${NC}"
    echo -e "${YELLOW}请先启动目标容器: docker-compose -f docker-compose.prod.yml up -d postgres${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 目标容器运行正常${NC}"

# 步骤5: 等待目标数据库就绪
echo -e "${YELLOW}[5/7] 等待目标数据库就绪...${NC}"
RETRY_COUNT=0
MAX_RETRIES=30
until docker exec "${TARGET_CONTAINER}" pg_isready -U "${TARGET_USER}" -d "${TARGET_DB}" > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo -e "${RED}✗ 数据库未能在预期时间内就绪${NC}"
        exit 1
    fi
    echo -n "."
    sleep 1
done
echo ""
echo -e "${GREEN}✓ 目标数据库已就绪${NC}"

# 步骤6: 导入数据
echo -e "${YELLOW}[6/7] 导入数据到目标数据库...${NC}"
echo "   数据库: ${TARGET_DB}"
echo "   容器: ${TARGET_CONTAINER}"

cat "${DUMP_FILE}" | docker exec -i "${TARGET_CONTAINER}" psql -U "${TARGET_USER}" -d "${TARGET_DB}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 数据导入成功${NC}"
else
    echo -e "${RED}✗ 数据导入失败！${NC}"
    echo -e "${YELLOW}请检查错误信息，可能需要手动修复${NC}"
    exit 1
fi

# 步骤7: 验证数据完整性
echo -e "${YELLOW}[7/7] 验证数据完整性...${NC}"

# 获取表数量
TABLE_COUNT=$(docker exec "${TARGET_CONTAINER}" psql -U "${TARGET_USER}" -d "${TARGET_DB}" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
TABLE_COUNT=$(echo $TABLE_COUNT | xargs)  # 去除空格

echo "   表数量: ${TABLE_COUNT}"

# 检查关键表
CRITICAL_TABLES=("test_cases" "execution_history" "execution_variables")
MISSING_TABLES=()

for table in "${CRITICAL_TABLES[@]}"; do
    EXISTS=$(docker exec "${TARGET_CONTAINER}" psql -U "${TARGET_USER}" -d "${TARGET_DB}" -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema='public' AND table_name='${table}');")
    EXISTS=$(echo $EXISTS | xargs)
    
    if [ "$EXISTS" = "t" ]; then
        # 获取记录数
        COUNT=$(docker exec "${TARGET_CONTAINER}" psql -U "${TARGET_USER}" -d "${TARGET_DB}" -t -c "SELECT COUNT(*) FROM ${table};")
        COUNT=$(echo $COUNT | xargs)
        echo "   ✓ ${table}: ${COUNT} 条记录"
    else
        MISSING_TABLES+=("$table")
        echo -e "   ${RED}✗ ${table}: 不存在${NC}"
    fi
done

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}迁移完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "备份文件: ${DUMP_FILE}"
echo "表总数: ${TABLE_COUNT}"

if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
    echo -e "${YELLOW}警告: 以下关键表缺失: ${MISSING_TABLES[*]}${NC}"
    echo -e "${YELLOW}请检查迁移是否完整${NC}"
fi

echo ""
echo -e "${GREEN}下一步操作:${NC}"
echo "1. 测试Web应用连接: docker-compose -f docker-compose.prod.yml up -d web-app"
echo "2. 检查应用日志: docker-compose -f docker-compose.prod.yml logs -f web-app"
echo "3. 访问Web界面验证功能"
echo ""
echo -e "${YELLOW}回滚方法（如需要）:${NC}"
echo "1. 停止新容器: docker-compose -f docker-compose.prod.yml down"
echo "2. 恢复旧配置并重新部署"
echo ""
