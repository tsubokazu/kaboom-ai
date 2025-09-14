import { UserRole } from "@/lib/auth-store";

interface UserRoleBadgeProps {
  role: UserRole;
  className?: string;
}

const roleConfig = {
  BASIC: {
    label: "ベーシック",
    color: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
    description: "基本的な取引・分析機能",
  },
  PREMIUM: {
    label: "プレミアム",
    color: "bg-blue-100 text-blue-800 dark:bg-blue-700 dark:text-blue-300",
    description: "高度なAI分析・バックテスト機能",
  },
  ADMIN: {
    label: "管理者",
    color: "bg-purple-100 text-purple-800 dark:bg-purple-700 dark:text-purple-300",
    description: "システム管理機能",
  },
};

export function UserRoleBadge({ role, className = "" }: UserRoleBadgeProps) {
  const config = roleConfig[role];

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color} ${className}`}
      title={config.description}
    >
      {config.label}
    </span>
  );
}