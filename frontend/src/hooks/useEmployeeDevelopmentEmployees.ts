import { useEffect, useRef, useState } from "react";
import { useAuth } from "./useAuth";
import { useEmployees } from "./useEmployees";
import { isSelfService } from "../lib/selfService";

/** Active employees for Employee Development pickers (HR/staff with employees read). */
export function useEmployeeDevelopmentEmployees(enabled = true) {
  const { user, hasPermission } = useAuth();
  const selfService = isSelfService(user);
  const canListEmployees = hasPermission("employees", "read");

  return {
    selfService,
    linkedEmployeeId: user?.linkedEmployeeId ?? null,
    canListEmployees,
    employees: useEmployees({
      status: "active",
      page: 1,
      pageSize: 200,
      enabled: enabled && !selfService && canListEmployees,
    }),
  };
}

/** Shared employee dropdown state — auto-picks first row once, respects manual choice after. */
export function useEmployeeDevelopmentSelection(
  employeesLoaded: boolean,
  items: { id: number }[] | undefined,
  options: { selfService: boolean; linkedEmployeeId?: number | null } = {
    selfService: false,
    linkedEmployeeId: null,
  },
) {
  const { selfService, linkedEmployeeId } = options;
  const [employeeId, setEmployeeIdState] = useState<number | "">("");
  const manualPick = useRef(false);

  useEffect(() => {
    if (selfService && linkedEmployeeId) {
      setEmployeeIdState(linkedEmployeeId);
      manualPick.current = true;
    }
  }, [selfService, linkedEmployeeId]);

  useEffect(() => {
    if (selfService || manualPick.current || employeeId !== "" || !employeesLoaded) return;
    const first = items?.[0];
    if (first) setEmployeeIdState(first.id);
  }, [selfService, employeeId, employeesLoaded, items]);

  function setEmployeeId(id: number | "") {
    manualPick.current = id !== "";
    setEmployeeIdState(id);
  }

  return { employeeId, setEmployeeId };
}
