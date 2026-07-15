import { ArrowLeftOutlined } from "@ant-design/icons";
import { Breadcrumb, Button, Space, Typography } from "antd";
import type { CSSProperties, ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";

const { Title, Text } = Typography;

/**
 * 面包屑条目
 * @see docs/02-design/ComponentLibrary.md §3.3
 */
export interface BreadcrumbItem {
  title: ReactNode;
  href?: string;
}

export interface PageHeaderProps {
  /** 主标题（H2） */
  title: ReactNode;
  /** 副标题（Caption Secondary） */
  description?: ReactNode;
  /** 面包屑 */
  breadcrumbs?: BreadcrumbItem[];
  /** 右侧主操作区 */
  extra?: ReactNode;
  /** 是否显示返回按钮（L3 详情页用） */
  back?: boolean | string;
  /** 自定义返回路径；不传则 history.back() */
  backHref?: string;
  /** 自定义 className */
  className?: string;
  /** 自定义内联样式 */
  style?: CSSProperties;
  /** 测试 ID */
  testId?: string;
}

/**
 * PageHeader - 业务页顶部统一头
 * @see docs/02-design/ComponentLibrary.md §3.3
 * @see docs/02-design/Wireframe.md §8.1
 */
export default function PageHeader({
  title,
  description,
  breadcrumbs,
  extra,
  back = false,
  backHref,
  className,
  style,
  testId,
}: PageHeaderProps) {
  const navigate = useNavigate();

  const handleBack = () => {
    if (backHref) {
      navigate(backHref);
    } else {
      navigate(-1);
    }
  };

  const backLabel = typeof back === "string" ? back : "返回";

  return (
    <div
      className={["page-header", className].filter(Boolean).join(" ")}
      style={style}
      data-testid={testId}
    >
      {breadcrumbs && breadcrumbs.length > 0 ? (
        <Breadcrumb
          className="page-breadcrumb"
          items={breadcrumbs.map((item, idx) => ({
            title:
              item.href && idx < breadcrumbs.length - 1 ? (
                <Link to={item.href}>{item.title}</Link>
              ) : (
                item.title
              ),
          }))}
          aria-label="面包屑导航"
        />
      ) : null}
      <div className="page-header-main">
        <Space direction="vertical" size={2}>
          {back ? (
            <Space size={8} align="center">
              <Button
                type="text"
                size="small"
                icon={<ArrowLeftOutlined />}
                onClick={handleBack}
                aria-label={backLabel}
              >
                {backLabel}
              </Button>
              <Title level={2} className="page-title" style={{ margin: 0 }}>
                {title}
              </Title>
            </Space>
          ) : (
            <Title level={2} className="page-title" style={{ margin: 0 }}>
              {title}
            </Title>
          )}
          {description ? <Text type="secondary">{description}</Text> : null}
        </Space>
        {extra ? <div className="page-header-extra">{extra}</div> : null}
      </div>
    </div>
  );
}