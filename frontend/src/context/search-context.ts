import { createContext, useContext } from "react";

export type SearchContextValue = {
  search: string;
  setSearch: (value: string) => void;
};

export const SearchContext = createContext<SearchContextValue | null>(null);

export function useSearch(): SearchContextValue {
  const context = useContext(SearchContext);

  if (context === null) {
    throw new Error("useSearch debe usarse dentro de <SearchProvider>");
  }

  return context;
}
