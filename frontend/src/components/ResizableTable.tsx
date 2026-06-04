import { useEffect, useMemo, useState } from 'react';
import type React from 'react';
import { Table } from 'antd';
import type { TableProps } from 'antd';
import type { ColumnsType, ColumnType } from 'antd/es/table';

type ResizableTableProps<T extends object> = Omit<TableProps<T>, 'columns'> & {
  columns: ColumnsType<T>;
  defaultColumnWidth?: number;
  minColumnWidth?: number;
  maxColumnWidth?: number;
};

type HeaderCellProps = React.ThHTMLAttributes<HTMLTableCellElement> & {
  width?: number;
  onResize?: (width: number) => void;
};

function getColumnKey<T extends object>(column: ColumnType<T>, index: number) {
  return String(column.key ?? column.dataIndex ?? `column-${index}`);
}

function cx(...values: Array<string | undefined>) {
  return values.filter(Boolean).join(' ');
}

function ResizableHeaderCell({ width, onResize, children, style, ...restProps }: HeaderCellProps) {
  const [dragging, setDragging] = useState(false);

  const handleMouseDown = (event: React.MouseEvent<HTMLSpanElement>) => {
    if (!width || !onResize) return;
    event.preventDefault();
    event.stopPropagation();
    const startX = event.clientX;
    const startWidth = width;
    setDragging(true);

    const handleMouseMove = (moveEvent: MouseEvent) => {
      onResize(startWidth + moveEvent.clientX - startX);
    };
    const handleMouseUp = () => {
      setDragging(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  return (
    <th
      {...restProps}
      style={{
        ...style,
        width,
        minWidth: width,
        position: 'relative'
      }}
    >
      {children}
      {width ? (
        <span
          className={`resizable-table-handle${dragging ? ' is-dragging' : ''}`}
          onMouseDown={handleMouseDown}
        />
      ) : null}
    </th>
  );
}

export default function ResizableTable<T extends object>({
  columns,
  defaultColumnWidth = 120,
  minColumnWidth = 80,
  maxColumnWidth = 600,
  scroll,
  ...tableProps
}: ResizableTableProps<T>) {
  const columnKeys = useMemo(() => columns.map((column, index) => getColumnKey(column as ColumnType<T>, index)), [columns]);
  const columnKeySignature = columnKeys.join('|');
  const defaultWidths = useMemo(
    () =>
      columns.reduce<Record<string, number>>((result, column, index) => {
        const key = columnKeys[index];
        const width = Number((column as ColumnType<T>).width ?? defaultColumnWidth);
        result[key] = Number.isFinite(width) && width > 0 ? width : defaultColumnWidth;
        return result;
      }, {}),
    [columnKeys, columns, defaultColumnWidth]
  );
  const [widths, setWidths] = useState(defaultWidths);

  useEffect(() => {
    setWidths((current) => {
      const next: Record<string, number> = {};
      columnKeys.forEach((key) => {
        next[key] = current[key] ?? defaultWidths[key] ?? defaultColumnWidth;
      });
      return next;
    });
  }, [columnKeySignature, columnKeys, defaultColumnWidth, defaultWidths]);

  const resizedColumns = useMemo(
    () =>
      columns.map((column, index) => {
        const key = columnKeys[index];
        const width = widths[key] ?? defaultWidths[key] ?? defaultColumnWidth;
        const originalOnHeaderCell = (column as ColumnType<T>).onHeaderCell as ((...args: unknown[]) => React.ThHTMLAttributes<HTMLTableCellElement>) | undefined;
        return {
          ...column,
          width,
          onHeaderCell: (...args: unknown[]) => ({
            ...(originalOnHeaderCell?.(...args) ?? {}),
            width,
            onResize: (nextWidth: number) => {
              setWidths((current) => ({
                ...current,
                [key]: Math.min(maxColumnWidth, Math.max(minColumnWidth, Math.round(nextWidth)))
              }));
            }
          })
        };
      }),
    [columnKeys, columns, defaultColumnWidth, defaultWidths, maxColumnWidth, minColumnWidth, widths]
  );

  const totalTableWidth = useMemo(
    () => resizedColumns.reduce((sum, column) => sum + Number(column.width ?? defaultColumnWidth), 0),
    [defaultColumnWidth, resizedColumns]
  );

  return (
    <Table<T>
      {...tableProps}
      className={cx('resizable-table', tableProps.className)}
      style={{
        ...tableProps.style,
        '--resizable-table-width': `${totalTableWidth}px`
      } as React.CSSProperties}
      tableLayout="fixed"
      columns={resizedColumns as unknown as ColumnsType<T>}
      components={{
        ...tableProps.components,
        header: {
          ...tableProps.components?.header,
          cell: ResizableHeaderCell
        }
      }}
      scroll={{ ...scroll, x: totalTableWidth }}
    />
  );
}
