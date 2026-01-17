"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/index.ts
var index_exports = {};
__export(index_exports, {
  Alert: () => Alert,
  AlertDescription: () => AlertDescription,
  AlertTitle: () => AlertTitle,
  Badge: () => Badge,
  Button: () => Button,
  Card: () => Card,
  CardContent: () => CardContent,
  CardDescription: () => CardDescription,
  CardFooter: () => CardFooter,
  CardHeader: () => CardHeader,
  CardTitle: () => CardTitle,
  Dialog: () => Dialog,
  DialogContent: () => DialogContent,
  DialogDescription: () => DialogDescription,
  DialogHeader: () => DialogHeader,
  DialogTitle: () => DialogTitle,
  DialogTrigger: () => DialogTrigger,
  Input: () => Input,
  Label: () => Label,
  Progress: () => Progress,
  Select: () => Select,
  SelectContent: () => SelectContent,
  SelectItem: () => SelectItem,
  SelectTrigger: () => SelectTrigger,
  SelectValue: () => SelectValue,
  Separator: () => Separator,
  Skeleton: () => Skeleton,
  Tabs: () => Tabs,
  TabsContent: () => TabsContent,
  TabsList: () => TabsList,
  TabsTrigger: () => TabsTrigger,
  cn: () => cn
});
module.exports = __toCommonJS(index_exports);

// src/components/button.tsx
var React = __toESM(require("react"));
var import_class_variance_authority = require("class-variance-authority");

// src/lib/utils.ts
var import_clsx = require("clsx");
var import_tailwind_merge = require("tailwind-merge");
function cn(...inputs) {
  return (0, import_tailwind_merge.twMerge)((0, import_clsx.clsx)(inputs));
}

// src/components/button.tsx
var import_jsx_runtime = require("react/jsx-runtime");
var buttonVariants = (0, import_class_variance_authority.cva)(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline"
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10"
      }
    },
    defaultVariants: {
      variant: "default",
      size: "default"
    }
  }
);
var Button = React.forwardRef(
  ({ className, variant, size, ...props }, ref) => {
    return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(
      "button",
      {
        className: cn(buttonVariants({ variant, size, className })),
        ref,
        ...props
      }
    );
  }
);
Button.displayName = "Button";

// src/components/card.tsx
var React2 = __toESM(require("react"));
var import_jsx_runtime2 = require("react/jsx-runtime");
var Card = React2.forwardRef(
  ({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(
    "div",
    {
      ref,
      className: cn("rounded-lg border bg-card text-card-foreground shadow-sm", className),
      ...props
    }
  )
);
Card.displayName = "Card";
var CardHeader = React2.forwardRef(
  ({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("div", { ref, className: cn("flex flex-col space-y-1.5 p-6", className), ...props })
);
CardHeader.displayName = "CardHeader";
var CardTitle = React2.forwardRef(
  ({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(
    "h3",
    {
      ref,
      className: cn("text-2xl font-semibold leading-none tracking-tight", className),
      ...props
    }
  )
);
CardTitle.displayName = "CardTitle";
var CardDescription = React2.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("p", { ref, className: cn("text-sm text-muted-foreground", className), ...props }));
CardDescription.displayName = "CardDescription";
var CardContent = React2.forwardRef(
  ({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("div", { ref, className: cn("p-6 pt-0", className), ...props })
);
CardContent.displayName = "CardContent";
var CardFooter = React2.forwardRef(
  ({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("div", { ref, className: cn("flex items-center p-6 pt-0", className), ...props })
);
CardFooter.displayName = "CardFooter";

// src/components/input.tsx
var React3 = __toESM(require("react"));
var import_jsx_runtime3 = require("react/jsx-runtime");
var Input = React3.forwardRef(
  ({ className, type, ...props }, ref) => {
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      "input",
      {
        type,
        className: cn(
          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        ),
        ref,
        ...props
      }
    );
  }
);
Input.displayName = "Input";

// src/components/label.tsx
var React4 = __toESM(require("react"));
var import_jsx_runtime4 = require("react/jsx-runtime");
var Label = React4.forwardRef(
  ({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(
    "label",
    {
      ref,
      className: cn(
        "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
        className
      ),
      ...props
    }
  )
);
Label.displayName = "Label";

// src/components/badge.tsx
var import_class_variance_authority2 = require("class-variance-authority");
var import_jsx_runtime5 = require("react/jsx-runtime");
var badgeVariants = (0, import_class_variance_authority2.cva)(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground"
      }
    },
    defaultVariants: {
      variant: "default"
    }
  }
);
function Badge({ className, variant, ...props }) {
  return /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("div", { className: cn(badgeVariants({ variant }), className), ...props });
}

// src/components/alert.tsx
var React5 = __toESM(require("react"));
var import_class_variance_authority3 = require("class-variance-authority");
var import_jsx_runtime6 = require("react/jsx-runtime");
var alertVariants = (0, import_class_variance_authority3.cva)(
  "relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground",
  {
    variants: {
      variant: {
        default: "bg-background text-foreground",
        destructive: "border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive"
      }
    },
    defaultVariants: {
      variant: "default"
    }
  }
);
var Alert = React5.forwardRef(({ className, variant, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime6.jsx)("div", { ref, role: "alert", className: cn(alertVariants({ variant }), className), ...props }));
Alert.displayName = "Alert";
var AlertTitle = React5.forwardRef(
  ({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime6.jsx)("h5", { ref, className: cn("mb-1 font-medium leading-none tracking-tight", className), ...props })
);
AlertTitle.displayName = "AlertTitle";
var AlertDescription = React5.forwardRef(
  ({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime6.jsx)("div", { ref, className: cn("text-sm [&_p]:leading-relaxed", className), ...props })
);
AlertDescription.displayName = "AlertDescription";

// src/components/dialog.tsx
var React6 = __toESM(require("react"));
var import_jsx_runtime7 = require("react/jsx-runtime");
var DialogContext = React6.createContext(void 0);
var Dialog = ({ open: controlledOpen, onOpenChange, children }) => {
  const [internalOpen, setInternalOpen] = React6.useState(false);
  const open = controlledOpen ?? internalOpen;
  const handleOpenChange = onOpenChange ?? setInternalOpen;
  return /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(DialogContext.Provider, { value: { open, onOpenChange: handleOpenChange }, children });
};
var DialogTrigger = React6.forwardRef(({ children, onClick, ...props }, ref) => {
  const context = React6.useContext(DialogContext);
  if (!context) throw new Error("DialogTrigger must be used within Dialog");
  return /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(
    "button",
    {
      ref,
      onClick: (e) => {
        context.onOpenChange(true);
        onClick?.(e);
      },
      ...props,
      children
    }
  );
});
DialogTrigger.displayName = "DialogTrigger";
var DialogContent = React6.forwardRef(({ className, children, ...props }, ref) => {
  const context = React6.useContext(DialogContext);
  if (!context) throw new Error("DialogContent must be used within Dialog");
  if (!context.open) return null;
  return /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)("div", { className: "fixed inset-0 z-50 flex items-center justify-center", children: [
    /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(
      "div",
      {
        className: "fixed inset-0 bg-black/50",
        onClick: () => context.onOpenChange(false)
      }
    ),
    /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(
      "div",
      {
        ref,
        className: cn(
          "relative z-50 w-full max-w-lg rounded-lg border bg-background p-6 shadow-lg",
          className
        ),
        ...props,
        children
      }
    )
  ] });
});
DialogContent.displayName = "DialogContent";
var DialogHeader = ({ className, ...props }) => /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: cn("flex flex-col space-y-1.5 text-center sm:text-left", className), ...props });
var DialogTitle = React6.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(
  "h2",
  {
    ref,
    className: cn("text-lg font-semibold leading-none tracking-tight", className),
    ...props
  }
));
DialogTitle.displayName = "DialogTitle";
var DialogDescription = React6.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("p", { ref, className: cn("text-sm text-muted-foreground", className), ...props }));
DialogDescription.displayName = "DialogDescription";

// src/components/select.tsx
var React7 = __toESM(require("react"));
var import_jsx_runtime8 = require("react/jsx-runtime");
var SelectContext = React7.createContext(void 0);
var Select = ({ value: controlledValue, onValueChange, children }) => {
  const [internalValue, setInternalValue] = React7.useState("");
  const [open, setOpen] = React7.useState(false);
  const value = controlledValue ?? internalValue;
  const handleValueChange = onValueChange ?? setInternalValue;
  return /* @__PURE__ */ (0, import_jsx_runtime8.jsx)(SelectContext.Provider, { value: { value, onValueChange: handleValueChange, open, onOpenChange: setOpen }, children });
};
var SelectTrigger = React7.forwardRef(({ className, children, ...props }, ref) => {
  const context = React7.useContext(SelectContext);
  if (!context) throw new Error("SelectTrigger must be used within Select");
  return /* @__PURE__ */ (0, import_jsx_runtime8.jsx)(
    "button",
    {
      ref,
      type: "button",
      onClick: () => context.onOpenChange(!context.open),
      className: cn(
        "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        className
      ),
      ...props,
      children
    }
  );
});
SelectTrigger.displayName = "SelectTrigger";
var SelectValue = ({ placeholder }) => {
  const context = React7.useContext(SelectContext);
  if (!context) throw new Error("SelectValue must be used within Select");
  return /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("span", { children: context.value || placeholder || "Select..." });
};
var SelectContent = React7.forwardRef(({ className, children, ...props }, ref) => {
  const context = React7.useContext(SelectContext);
  if (!context) throw new Error("SelectContent must be used within Select");
  if (!context.open) return null;
  return /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)("div", { className: "relative z-50", children: [
    /* @__PURE__ */ (0, import_jsx_runtime8.jsx)(
      "div",
      {
        className: "fixed inset-0",
        onClick: () => context.onOpenChange(false)
      }
    ),
    /* @__PURE__ */ (0, import_jsx_runtime8.jsx)(
      "div",
      {
        ref,
        className: cn(
          "absolute z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md",
          className
        ),
        ...props,
        children
      }
    )
  ] });
});
SelectContent.displayName = "SelectContent";
var SelectItem = React7.forwardRef(({ className, children, value, ...props }, ref) => {
  const context = React7.useContext(SelectContext);
  if (!context) throw new Error("SelectItem must be used within Select");
  return /* @__PURE__ */ (0, import_jsx_runtime8.jsx)(
    "div",
    {
      ref,
      className: cn(
        "relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 px-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground",
        context.value === value && "bg-accent text-accent-foreground",
        className
      ),
      onClick: () => {
        context.onValueChange(value);
        context.onOpenChange(false);
      },
      ...props,
      children
    }
  );
});
SelectItem.displayName = "SelectItem";

// src/components/tabs.tsx
var React8 = __toESM(require("react"));
var import_jsx_runtime9 = require("react/jsx-runtime");
var TabsContext = React8.createContext(void 0);
var Tabs = ({ value: controlledValue, onValueChange, defaultValue, children }) => {
  const [internalValue, setInternalValue] = React8.useState(defaultValue || "");
  const value = controlledValue ?? internalValue;
  const handleValueChange = onValueChange ?? setInternalValue;
  return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(TabsContext.Provider, { value: { value, onValueChange: handleValueChange }, children });
};
var TabsList = React8.forwardRef(
  ({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(
    "div",
    {
      ref,
      className: cn(
        "inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground",
        className
      ),
      ...props
    }
  )
);
TabsList.displayName = "TabsList";
var TabsTrigger = React8.forwardRef(({ className, value, ...props }, ref) => {
  const context = React8.useContext(TabsContext);
  if (!context) throw new Error("TabsTrigger must be used within Tabs");
  return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(
    "button",
    {
      ref,
      type: "button",
      onClick: () => context.onValueChange(value),
      className: cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        context.value === value ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:bg-background/50",
        className
      ),
      ...props
    }
  );
});
TabsTrigger.displayName = "TabsTrigger";
var TabsContent = React8.forwardRef(({ className, value, ...props }, ref) => {
  const context = React8.useContext(TabsContext);
  if (!context) throw new Error("TabsContent must be used within Tabs");
  if (context.value !== value) return null;
  return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(
    "div",
    {
      ref,
      className: cn(
        "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        className
      ),
      ...props
    }
  );
});
TabsContent.displayName = "TabsContent";

// src/components/progress.tsx
var React9 = __toESM(require("react"));
var import_jsx_runtime10 = require("react/jsx-runtime");
var Progress = React9.forwardRef(
  ({ className, value = 0, max = 100, ...props }, ref) => {
    const percentage = Math.min(Math.max(value / max * 100, 0), 100);
    return /* @__PURE__ */ (0, import_jsx_runtime10.jsx)(
      "div",
      {
        ref,
        className: cn("relative h-4 w-full overflow-hidden rounded-full bg-secondary", className),
        ...props,
        children: /* @__PURE__ */ (0, import_jsx_runtime10.jsx)(
          "div",
          {
            className: "h-full w-full flex-1 bg-primary transition-all",
            style: { transform: `translateX(-${100 - percentage}%)` }
          }
        )
      }
    );
  }
);
Progress.displayName = "Progress";

// src/components/separator.tsx
var React10 = __toESM(require("react"));
var import_jsx_runtime11 = require("react/jsx-runtime");
var Separator = React10.forwardRef(
  ({ className, orientation = "horizontal", decorative = true, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime11.jsx)(
    "div",
    {
      ref,
      role: decorative ? "none" : "separator",
      "aria-orientation": orientation,
      className: cn(
        "shrink-0 bg-border",
        orientation === "horizontal" ? "h-[1px] w-full" : "h-full w-[1px]",
        className
      ),
      ...props
    }
  )
);
Separator.displayName = "Separator";

// src/components/skeleton.tsx
var import_jsx_runtime12 = require("react/jsx-runtime");
function Skeleton({ className, ...props }) {
  return /* @__PURE__ */ (0, import_jsx_runtime12.jsx)("div", { className: cn("animate-pulse rounded-md bg-muted", className), ...props });
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  Alert,
  AlertDescription,
  AlertTitle,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Input,
  Label,
  Progress,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Separator,
  Skeleton,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  cn
});
//# sourceMappingURL=index.js.map