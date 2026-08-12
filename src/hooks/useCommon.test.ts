import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAsyncOperation, useSelection, useFilteredList } from "@/hooks/useCommon";

describe("useAsyncOperation", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("should initialize with loading false and no toast", () => {
    const { result } = renderHook(() => useAsyncOperation());
    
    expect(result.current.loading).toBe(false);
    expect(result.current.toast).toBeNull();
  });

  it("should show success toast on successful operation", async () => {
    const { result } = renderHook(() => useAsyncOperation());
    
    await act(async () => {
      await result.current.execute(
        () => Promise.resolve("data"),
        { successMessage: "Success!" }
      );
    });

    expect(result.current.toast).toEqual({
      message: "Success!",
      type: "success",
    });
  });

  it("should show error toast on failed operation", async () => {
    const { result } = renderHook(() => useAsyncOperation());
    
    await act(async () => {
      await result.current.execute(
        () => Promise.reject(new Error("Failed")),
        { errorMessage: "Custom error" }
      );
    });

    expect(result.current.toast).toEqual({
      message: "Custom error",
      type: "error",
    });
  });

  it("should manage loading state during operation", async () => {
    const { result } = renderHook(() => useAsyncOperation());
    
    let resolvePromise: (value: string) => void;
    const promise = new Promise<string>((resolve) => {
      resolvePromise = resolve;
    });

    act(() => {
      result.current.execute(() => promise);
    });

    expect(result.current.loading).toBe(true);

    await act(async () => {
      resolvePromise!("done");
      await promise;
    });

    expect(result.current.loading).toBe(false);
  });

  it("should clear toast after timeout", async () => {
    const { result } = renderHook(() => useAsyncOperation());
    
    act(() => {
      result.current.showToast("Test message", "info");
    });

    expect(result.current.toast).not.toBeNull();

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.toast).toBeNull();
  });
});

describe("useSelection", () => {
  const mockItems = [
    { id: "1", name: "Item 1" },
    { id: "2", name: "Item 2" },
    { id: "3", name: "Item 3" },
  ];

  it("should initialize with empty selection", () => {
    const { result } = renderHook(() => useSelection(mockItems));
    
    expect(result.current.items).toEqual(mockItems);
    expect(result.current.selected).toBeNull();
    expect(result.current.selectedId).toBeNull();
  });

  it("should select an item", () => {
    const { result } = renderHook(() => useSelection(mockItems));
    
    act(() => {
      result.current.select(mockItems[1]);
    });

    expect(result.current.selected).toEqual(mockItems[1]);
    expect(result.current.selectedId).toBe("2");
  });

  it("should add an item and select it", () => {
    const { result } = renderHook(() => useSelection(mockItems));
    const newItem = { id: "4", name: "Item 4" };
    
    act(() => {
      result.current.add(newItem);
    });

    expect(result.current.items).toHaveLength(4);
    expect(result.current.items[0]).toEqual(newItem);
    expect(result.current.selectedId).toBe("4");
  });

  it("should remove an item and clear selection if selected", () => {
    const { result } = renderHook(() => useSelection(mockItems));
    
    act(() => {
      result.current.select(mockItems[1]);
    });

    act(() => {
      result.current.remove("2");
    });

    expect(result.current.items).toHaveLength(2);
    expect(result.current.selectedId).toBeNull();
  });

  it("should update an item", () => {
    const { result } = renderHook(() => useSelection(mockItems));
    
    act(() => {
      result.current.update("2", (item) => ({ ...item, name: "Updated" }));
    });

    expect(result.current.items[1].name).toBe("Updated");
  });
});

describe("useFilteredList", () => {
  const items = [
    { id: "1", name: "Apple" },
    { id: "2", name: "Banana" },
    { id: "3", name: "Cherry" },
  ];

  const filterFn = (item: typeof items[0], query: string) =>
    item.name.toLowerCase().includes(query);

  it("should return all items when no filter", () => {
    const { result } = renderHook(() => useFilteredList(items, filterFn));
    
    expect(result.current.filtered).toEqual(items);
    expect(result.current.hasFilter).toBe(false);
  });

  it("should filter items by query", () => {
    const { result } = renderHook(() => useFilteredList(items, filterFn));
    
    act(() => {
      result.current.setQuery("an");
    });

    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].name).toBe("Banana");
    expect(result.current.hasFilter).toBe(true);
  });

  it("should clear filter", () => {
    const { result } = renderHook(() => useFilteredList(items, filterFn));
    
    act(() => {
      result.current.setQuery("an");
    });

    act(() => {
      result.current.clear();
    });

    expect(result.current.filtered).toEqual(items);
    expect(result.current.hasFilter).toBe(false);
  });
});
