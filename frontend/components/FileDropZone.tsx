"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, Loader2 } from "lucide-react";

const ACCEPTED = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
};

interface Props {
  onFiles: (files: File[]) => void;
  isLoading: boolean;
}

export function FileDropZone({ onFiles, isLoading }: Props) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0 && !isLoading) onFiles(accepted);
    },
    [onFiles, isLoading]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 10,
    disabled: isLoading,
  });

  return (
    <div
      {...getRootProps()}
      className={`relative flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-5 text-center cursor-pointer transition-colors select-none ${
        isDragActive
          ? "border-blue-500 bg-blue-950/30"
          : "border-bg-border hover:border-blue-500 hover:bg-bg-elevated"
      } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <input {...getInputProps()} />
      {isLoading ? (
        <Loader2 size={20} className="text-blue-400 animate-spin" />
      ) : (
        <Upload size={20} className="text-slate-500" />
      )}
      <p className="text-xs text-slate-500 leading-relaxed">
        {isLoading
          ? "Indexing..."
          : isDragActive
          ? "Drop files here"
          : "Drop files or click to upload"}
      </p>
      <p className="text-[10px] text-slate-600">PDF · DOCX · TXT · MD · max 10 files</p>
    </div>
  );
}
