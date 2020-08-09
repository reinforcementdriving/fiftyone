import { useState, useEffect } from "react";
import { useSubscribe } from "./socket";

const PAGE_SIZE = 5;

export const useSampleNavigation = (socket) => {
  const [currentId, setCurrentId] = useState(undefined);
  const [ids, setIds] = useState([]);
  const [page, setPage] = useState(0);
  const [isLast, setLast] = useState(false);

  const reset = () => {
    setCurrentId(undefined);
    setIds([]);
    setPage(0);
    setLast(false);
  };

  useSubscribe(socket, "update", reset);

  const updateFromPageResponse = (newPage, response) => {
    console.log({ response, newPage });
    setPage(newPage);
    setIds(response.results);
    setLast(response.more === false);
  };

  const movePrevious = () => {
    const newIndex = ids.indexOf(currentId) - 1;
    if (newIndex >= 0) {
      setCurrentId(ids[newIndex]);
    } else {
      const newPage = page - 1;
      socket.emit("page", newPage, PAGE_SIZE, true, (response) => {
        updateFromPageResponse(newPage, response);
        setCurrentId(response.results[response.results.length - 1]);
      });
    }
  };

  const moveNext = () => {
    const newIndex = ids.indexOf(currentId) + 1;
    if (newIndex < ids.length) {
      setCurrentId(ids[newIndex]);
    } else {
      const newPage = page + 1;
      socket.emit("page", newPage, PAGE_SIZE, true, (response) => {
        updateFromPageResponse(newPage, response);
        setCurrentId(response.results[0]);
      });
    }
  };

  return {
    reset,
    currentId,
    hasPrevious: page > 0 || ids.indexOf(currentId) > 0,
    hasNext: !isLast || ids.indexOf(currentId) < ids.length - 1,
    movePrevious,
    moveNext,
  };
};
