; ModuleID = 'example 4.c'
source_filename = "example 4.c"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@global_var1 = dso_local global i32 0, align 4
@.str = private unnamed_addr constant [5 x i8] c"cool\00", align 1
@global_var3 = dso_local global i8* getelementptr inbounds ([5 x i8], [5 x i8]* @.str, i32 0, i32 0), align 8
@global_var2 = dso_local global i32 0, align 4
@.str.1 = private unnamed_addr constant [8 x i8] c"so cool\00", align 1

; Function Attrs: noinline nounwind optnone uwtable
define dso_local i32 @main() #0 {
  %1 = alloca i32, align 4
  %2 = alloca i8, align 1
  %3 = alloca i32*, align 8
  store i32 0, i32* %1, align 4
  %4 = load i32, i32* @global_var1, align 4
  %5 = add nsw i32 %4, 1
  store i32 %5, i32* @global_var1, align 4
  %6 = load i32, i32* @global_var1, align 4
  %7 = add nsw i32 %6, 1
  store i32 %7, i32* @global_var2, align 4
  %8 = load i8*, i8** @global_var3, align 8
  %9 = getelementptr inbounds i8, i8* %8, i64 1
  %10 = load i8, i8* %9, align 1
  store i8 %10, i8* %2, align 1
  %11 = call noalias i8* @malloc(i64 4) #3
  %12 = bitcast i8* %11 to i32*
  store i32* %12, i32** %3, align 8
  %13 = load i32, i32* @global_var1, align 4
  %14 = load i32, i32* @global_var2, align 4
  %15 = call i32 @example(i32 1, i32 2, i32 %13, i32 %14)
  %16 = load i32*, i32** %3, align 8
  store i32 %15, i32* %16, align 4
  %17 = call i32 @puts(i8* getelementptr inbounds ([8 x i8], [8 x i8]* @.str.1, i64 0, i64 0))
  %18 = load i32*, i32** %3, align 8
  %19 = load i32, i32* %18, align 4
  ret i32 %19
}

; Function Attrs: nounwind
declare dso_local noalias i8* @malloc(i64) #1

; Function Attrs: noinline nounwind optnone uwtable
define dso_local i32 @example(i32 %0, i32 %1, i32 %2, i32 %3) #0 {
  %5 = alloca i32, align 4
  %6 = alloca i32, align 4
  %7 = alloca i32, align 4
  %8 = alloca i32, align 4
  %9 = alloca i32, align 4
  %10 = alloca i32, align 4
  %11 = alloca i32, align 4
  %12 = alloca i32, align 4
  %13 = alloca i32, align 4
  %14 = alloca i32, align 4
  %15 = alloca i32, align 4
  %16 = alloca i32, align 4
  store i32 %0, i32* %5, align 4
  store i32 %1, i32* %6, align 4
  store i32 %2, i32* %7, align 4
  store i32 %3, i32* %8, align 4
  br label %17

17:                                               ; preds = %52, %4
  %18 = load i32, i32* %5, align 4
  %19 = load i32, i32* %14, align 4
  %20 = icmp sgt i32 %18, %19
  br i1 %20, label %21, label %56

21:                                               ; preds = %17
  %22 = load i32, i32* %6, align 4
  store i32 %22, i32* %10, align 4
  %23 = load i32, i32* %7, align 4
  %24 = load i32, i32* %10, align 4
  %25 = add nsw i32 %23, %24
  store i32 %25, i32* %11, align 4
  %26 = load i32, i32* %8, align 4
  %27 = load i32, i32* %6, align 4
  %28 = sub nsw i32 %26, %27
  store i32 %28, i32* %12, align 4
  %29 = load i32, i32* %5, align 4
  %30 = load i32, i32* %11, align 4
  %31 = mul nsw i32 %29, %30
  store i32 %31, i32* %5, align 4
  %32 = load i32, i32* %5, align 4
  %33 = load i32, i32* %7, align 4
  %34 = srem i32 %32, %33
  store i32 %34, i32* %13, align 4
  %35 = load i32, i32* %5, align 4
  %36 = load i32, i32* %8, align 4
  %37 = add nsw i32 %35, %36
  store i32 %37, i32* %16, align 4
  %38 = load i32, i32* %5, align 4
  %39 = load i32, i32* %8, align 4
  %40 = icmp sgt i32 %38, %39
  br i1 %40, label %41, label %48

41:                                               ; preds = %21
  %42 = load i32, i32* %5, align 4
  store i32 %42, i32* %9, align 4
  %43 = load i32, i32* %13, align 4
  %44 = add nsw i32 %43, 3
  store i32 %44, i32* %5, align 4
  %45 = load i32, i32* %9, align 4
  %46 = load i32, i32* %6, align 4
  %47 = shl i32 %45, %46
  store i32 %47, i32* %14, align 4
  br label %52

48:                                               ; preds = %21
  %49 = load i32, i32* %5, align 4
  %50 = load i32, i32* %10, align 4
  %51 = shl i32 %49, %50
  store i32 %51, i32* %14, align 4
  br label %52

52:                                               ; preds = %48, %41
  %53 = load i32, i32* %5, align 4
  %54 = load i32, i32* %6, align 4
  %55 = shl i32 %53, %54
  store i32 %55, i32* %15, align 4
  br label %17

56:                                               ; preds = %17
  %57 = load i32, i32* %12, align 4
  %58 = load i32, i32* %15, align 4
  %59 = add nsw i32 %57, %58
  ret i32 %59
}

declare dso_local i32 @puts(i8*) #2

attributes #0 = { noinline nounwind optnone uwtable "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "frame-pointer"="all" "less-precise-fpmad"="false" "min-legal-vector-width"="0" "no-infs-fp-math"="false" "no-jump-tables"="false" "no-nans-fp-math"="false" "no-signed-zeros-fp-math"="false" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="false" "use-soft-float"="false" }
attributes #1 = { nounwind "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "frame-pointer"="all" "less-precise-fpmad"="false" "no-infs-fp-math"="false" "no-nans-fp-math"="false" "no-signed-zeros-fp-math"="false" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="false" "use-soft-float"="false" }
attributes #2 = { "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "frame-pointer"="all" "less-precise-fpmad"="false" "no-infs-fp-math"="false" "no-nans-fp-math"="false" "no-signed-zeros-fp-math"="false" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="false" "use-soft-float"="false" }
attributes #3 = { nounwind }

!llvm.module.flags = !{!0}
!llvm.ident = !{!1}

!0 = !{i32 1, !"wchar_size", i32 4}
!1 = !{!"Ubuntu clang version 11.1.0-++20211011094159+1fdec59bffc1-1~exp1~20211011214614.8"}
