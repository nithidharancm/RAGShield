export const DEMO_USERS = [
  {
    id: "user_001",
    tenant: "tenant_a",
    label: "Demo User A",
    short: "A",
    accent: "blue",
  },
  {
    id: "user_002",
    tenant: "tenant_b",
    label: "Demo User B",
    short: "B",
    accent: "violet",
  },
  {
    id: "user_003",
    tenant: "tenant_c",
    label: "Demo User C",
    short: "C",
    accent: "cyan",
  },
];

export function getUser(userId) {
  return DEMO_USERS.find((user) => user.id === userId) || DEMO_USERS[0];
}
